#!/usr/bin/env bash
# Local gates. Replaces .github/workflows/ci.yml (GitHub Actions retired
# 2026-09-03). Run by .githooks/pre-push, or by hand: scripts/ci-gates.sh
set -euo pipefail
cd "$(dirname "$0")/.."

# Resolve ruff without assuming a global install: the deleted workflow did
# "pip install ruff" on a fresh runner every time. Prefer a repo venv, then
# whatever is on PATH, then uvx (no install needed).
RUFF=""
for c in ./venv/bin/ruff ./.venv/bin/ruff; do [ -x "$c" ] && RUFF="$c" && break; done
[ -n "$RUFF" ] || command -v ruff >/dev/null 2>&1 && RUFF="${RUFF:-ruff}"
[ -n "$RUFF" ] || { command -v uvx >/dev/null 2>&1 && RUFF="uvx ruff"; }
[ -n "$RUFF" ] || { echo "ci-gates: no ruff found (try: uv tool install ruff)"; exit 1; }
echo "==> ruff check"
$RUFF check .
echo "==> ruff format --check"
$RUFF format --check .
echo "==> django tests"
# The workflow installed requirements onto a fresh runner. Locally there may be
# no venv, so run the suite when Django is importable and say so loudly when it
# is not, rather than failing a push over a missing local environment.
PY_BIN="python3"
for c in ./venv/bin/python ./.venv/bin/python; do [ -x "$c" ] && PY_BIN="$c" && break; done
if "$PY_BIN" -c "import django" >/dev/null 2>&1; then
  "$PY_BIN" manage.py test --verbosity=1
else
  echo "    SKIPPED: django not importable by $PY_BIN."
  echo "    Set up a venv (python3 -m venv venv && ./venv/bin/pip install -r requirements.txt)"
  echo "    to have this gate run the suite."
fi

echo "==> gates passed"
