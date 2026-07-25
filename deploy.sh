#!/bin/bash
#
# Deployment script for WrestlingDB — NUC target.
#
# History: this script used to target a DigitalOcean droplet at 137.184.7.163
# (/opt/owdb). That droplet is gone and the IP has since been reassigned to an
# unrelated third party — it currently serves a 3CX phone system on :443 under
# a Let's Encrypt cert for ablvsolutions.tx.3cx.us. The old script would SSH
# into that host as `eric` and run `sudo docker compose build/restart`, so it
# was replaced rather than repaired. See ROS-1206.
#
# Production now runs on the NUC (192.168.68.56) at ~/wrestlingdb, behind a
# cloudflared tunnel. There is no public :22/:80 — reach it over LAN/Tailscale.
#
# Usage:
#   ./deploy.sh                     # dry run: report only, change nothing
#   ./deploy.sh --apply             # deploy code; refuses if migrations pending
#   ./deploy.sh --apply --migrate   # deploy code AND apply pending migrations
#
# The migration gate is deliberate. The container CMD runs
# `manage.py migrate --noinput` at boot, so a plain `docker compose up -d`
# applies whatever is pending with no review step. This script forces you to
# see the pending list and take a backup first.

set -euo pipefail

SSH_HOST="${OWDB_SSH_HOST:-nuc}"
DEPLOY_PATH="${OWDB_DEPLOY_PATH:-/home/eric/wrestlingdb}"
BRANCH="${OWDB_BRANCH:-main}"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.nuc.yml"

APPLY=0
MIGRATE=0
for arg in "$@"; do
  case "$arg" in
    --apply)   APPLY=1 ;;
    --migrate) MIGRATE=1 ;;
    -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
remote() { ssh -o BatchMode=yes -o ConnectTimeout=15 "$SSH_HOST" "$@"; }

say "Target"
echo "  host:   $SSH_HOST"
echo "  path:   $DEPLOY_PATH"
echo "  branch: $BRANCH"
[ "$APPLY" -eq 1 ] || echo "  MODE:   dry run (pass --apply to actually deploy)"

say "Reachability"
remote "hostname && test -d '$DEPLOY_PATH'" \
  || { echo "cannot reach $SSH_HOST, or $DEPLOY_PATH is missing" >&2; exit 1; }

# The prod tree is historically an rsync snapshot, not a git checkout. Detect
# which one is there so a `git` update path doesn't silently no-op.
say "Prod tree type"
if remote "test -d '$DEPLOY_PATH/.git'"; then
  TREE=git
  echo "  git checkout — will fetch and reset to origin/$BRANCH"
  remote "cd '$DEPLOY_PATH' && git rev-parse --short HEAD"
else
  TREE=snapshot
  echo "  NOT a git checkout (rsync snapshot). Convert it once with:"
  echo "    ssh $SSH_HOST 'cd $DEPLOY_PATH && git init && \\"
  echo "      git remote add origin https://github.com/ericrosenberg1/OWDB.git && \\"
  echo "      git fetch origin $BRANCH && git reset --mixed origin/$BRANCH'"
  echo "  (--mixed keeps working-tree files. Review 'git status' afterwards —"
  echo "   prod carries local drift that is not in the repo.)"
fi

say "Pending migrations"
# `grep -c` exits 1 on a zero count, so swallow that inside the remote shell —
# otherwise a clean prod reads as an error instead of "nothing pending".
PENDING=$(remote "cd '$DEPLOY_PATH' && $COMPOSE exec -T web python manage.py showmigrations --plan 2>/dev/null | grep -c '^\[ \]' || true") || PENDING="?"
echo "  unapplied: $PENDING"

if [ "$PENDING" != "0" ] && [ "$PENDING" != "?" ]; then
  echo
  remote "cd '$DEPLOY_PATH' && $COMPOSE exec -T web python manage.py showmigrations --plan 2>/dev/null | grep '^\[ \]'" || true
  echo
  if [ "$MIGRATE" -ne 1 ]; then
    echo "Refusing to deploy with $PENDING unapplied migration(s)." >&2
    echo "Review the SQL first:" >&2
    echo "  ssh $SSH_HOST \"cd $DEPLOY_PATH && $COMPOSE exec -T web python manage.py sqlmigrate <app> <number>\"" >&2
    echo "Then re-run with --apply --migrate." >&2
    exit 3
  fi
fi

if [ "$APPLY" -ne 1 ]; then
  say "Dry run complete — nothing changed."
  exit 0
fi

# Back up SQLite before any schema change. sqlite3 .backup is safe against a
# live DB; a plain cp can capture a torn page mid-write.
if [ "$MIGRATE" -eq 1 ] && [ "$PENDING" != "0" ]; then
  say "Backing up SQLite"
  STAMP=$(date +%Y%m%d-%H%M%S)
  remote "cd '$DEPLOY_PATH' && sqlite3 data/db.sqlite3 \".backup 'data/db.sqlite3.pre-deploy-$STAMP'\" && ls -lh 'data/db.sqlite3.pre-deploy-$STAMP'"
  echo "  rollback: stop web, restore that file over data/db.sqlite3, restart"
fi

say "Updating code"
if [ "$TREE" = git ]; then
  remote "cd '$DEPLOY_PATH' && git fetch origin '$BRANCH' && git reset --hard 'origin/$BRANCH' && git rev-parse --short HEAD"
else
  echo "  snapshot tree — rsync your working copy, then re-run. Not automated on" >&2
  echo "  purpose: rsyncing over prod is how the tree drifted six weeks in the" >&2
  echo "  first place (ROS-1206). Convert to a checkout using the command above." >&2
  exit 4
fi

say "Rebuilding and restarting"
remote "cd '$DEPLOY_PATH' && $COMPOSE up -d --build"

say "Waiting for health"
STATUS=starting
for i in $(seq 1 30); do
  STATUS=$(remote "docker inspect --format '{{.State.Health.Status}}' wrestlingdb-web-1 2>/dev/null" || echo starting)
  echo "  [$i/30] $STATUS"
  [ "$STATUS" = healthy ] && break
  sleep 5
done
[ "$STATUS" = healthy ] || { echo "web never became healthy — ssh $SSH_HOST 'docker logs wrestlingdb-web-1'" >&2; exit 5; }

say "Post-deploy checks"
remote "cd '$DEPLOY_PATH' && { $COMPOSE exec -T web python manage.py showmigrations --plan 2>/dev/null | grep -c '^\[ \]' || true; } | xargs echo '  unapplied migrations:'"
remote "docker exec wrestlingdb-web-1 curl -sS -o /dev/null -w '  health endpoint: %{http_code}\n' -H 'Host: wrestlingdb.org' http://127.0.0.1:8000/health/" || true

say "Deployed"
echo "  Public: https://wrestlingdb.org"
echo "  Logs:   ssh $SSH_HOST 'docker logs -f wrestlingdb-web-1'"
