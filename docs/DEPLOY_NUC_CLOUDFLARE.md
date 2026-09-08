# Deploying OWDB on the NUC behind Cloudflare Tunnel

The cheapest production-ready setup for this Django + Postgres + Redis +
Celery + R2 stack until traffic justifies a paid VPS.

## Why this setup

| Option | Verdict |
|---|---|
| **NUC + Cloudflare Tunnel** | Recommended. ~$0/mo marginal cost (electricity only). |
| Cloudflare Pages (static) | Won't work — site is server-side Django + Postgres, not static. |
| Cloudflare Workers + D1 | Same problem. Whole stack would need a rewrite. |
| Render free tier | Sleeps after 15 min inactivity → 30 s cold start kills first paint. |
| Fly.io free tier | Works, but free Postgres is 90 days; $7/mo after. |
| DigitalOcean droplet | What was running before. $6-12/mo. Fine, but unnecessary while NUC is idle. |

A Cloudflare Tunnel gives you:
- Free TLS termination at the edge — no certbot, no Let's Encrypt renewal
- Hidden origin IP (the NUC's public IP is never exposed)
- DDoS protection at no cost
- Works behind NAT / CGNAT / consumer ISP without port forwarding
- 100 GB/month free egress through the tunnel; OWDB's bandwidth is dominated
  by images, which already go through R2 + Cloudflare CDN, not the tunnel

The two things you pay for at this stage:
- Electricity for the NUC (already on for development → marginal $0)
- The domain registration on `wrestlingdb.org` (already paid)
- R2 storage — Cloudflare's free tier covers 10 GB + 1M class A ops/mo;
  OWDB images at ~200 KB each × ~300 wrestlers = ~60 MB, well under

## What to expect

- **Cold-start latency:** none — gunicorn stays running under systemd
- **First-request latency:** ~200-400 ms from US to NUC via Cloudflare edge
- **Concurrent users:** the NUC easily handles 50-100 concurrent sessions
  at this DB size; if/when you outgrow it, migrate to a $6/mo droplet
- **Outage exposure:** home internet down = site down. Acceptable until
  you start showing it to investors / shipping affiliate links.

## Step 1 — Fix the stale DNS at Cloudflare (do this NOW)

The current `A wrestlingdb.org 137.184.7.163` record points at a
DigitalOcean IP that has been recycled to someone else's 3CX phone system.
Anyone hitting `https://wrestlingdb.org` right now sees that 3CX server's
TLS cert. Fix even before deploying anything:

1. Log in to Cloudflare → wrestlingdb.org → DNS
2. Delete the `A` record for `@` pointing at `137.184.7.163`
3. Delete the `A` record for `www` pointing at the same IP (if present)

After step 1 the domain returns NXDOMAIN. That's fine — better than the
3CX cert error users see today. Cloudflare Tunnel adds the right CNAMEs
in step 4 automatically.

**Leave `images.wrestlingdb.org` alone** — that's the R2 custom domain
and is still working correctly.

## Step 2 — Provision the NUC

Production environment file at `/home/wrestlingdb/.env`:

```bash
# Django
APP_ENV=production
APP_SECRET_KEY=<generate fresh: python -c 'import secrets; print(secrets.token_urlsafe(64))'>
DEBUG=0
ALLOWED_HOSTS=wrestlingdb.org,www.wrestlingdb.org

# Database (Postgres on the NUC)
DB_ENGINE=postgres
DB_NAME=owdb
DB_USER=owdb
DB_PASSWORD=<strong password>
DB_HOST=localhost
DB_PORT=5432

# Redis (also on the NUC)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# R2 (unchanged from existing setup)
R2_ACCESS_KEY_ID=<from Cloudflare R2 dashboard>
R2_SECRET_ACCESS_KEY=<from Cloudflare R2 dashboard>
R2_BUCKET_NAME=owdb-images
R2_ACCOUNT_ID=ab3678edc12d723ab959fb449b095bc6
R2_CUSTOM_DOMAIN=images.wrestlingdb.org

# Email
DEFAULT_FROM_EMAIL=OWDB <noreply@wrestlingdb.org>
SERVER_EMAIL=errors@wrestlingdb.org
# (Wire SMTP later — Postmark / SES / Resend free tier; not blocking launch)

# API keys for the agents
ANTHROPIC_API_KEY=<existing>
BRAVE_SEARCH_API_KEY=<existing>
TAVILY_API_KEY=<existing>
```

Then install services. Ubuntu/Debian assumed:

```bash
# 1. System packages
sudo apt update
sudo apt install -y python3.12 python3.12-venv postgresql-15 redis-server \
    nginx git build-essential libpq-dev

# 2. App user + repo
sudo adduser --system --group --home /home/wrestlingdb wrestlingdb
sudo -u wrestlingdb -i
cd /home/wrestlingdb
git clone https://github.com/ericrosenberg1/OWDB.git app
cd app
python3.12 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/pip install gunicorn  # not already in requirements

# 3. Postgres
sudo -u postgres createuser owdb --pwprompt
sudo -u postgres createdb owdb -O owdb

# 4. First migration + collect static
sudo -u wrestlingdb -i
cd app && source venv/bin/activate
export $(cat /home/wrestlingdb/.env | grep -v '^#' | xargs)
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser  # for admin access
```

## Step 3 — systemd services

Three units: gunicorn for the web, celery worker for agents, celery beat
for the schedule.

**`/etc/systemd/system/wrestlingdb-web.service`**
```ini
[Unit]
Description=OWDB Django web (gunicorn)
After=network.target postgresql.service redis-server.service

[Service]
Type=notify
User=wrestlingdb
Group=wrestlingdb
WorkingDirectory=/home/wrestlingdb/app
EnvironmentFile=/home/wrestlingdb/.env
ExecStart=/home/wrestlingdb/app/venv/bin/gunicorn \
  --bind 127.0.0.1:8000 \
  --workers 3 \
  --timeout 60 \
  --access-logfile - \
  owdb_django.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/wrestlingdb-celery.service`**
```ini
[Unit]
Description=OWDB Celery worker (JR / Al / Earl agents)
After=network.target redis-server.service postgresql.service

[Service]
Type=simple
User=wrestlingdb
Group=wrestlingdb
WorkingDirectory=/home/wrestlingdb/app
EnvironmentFile=/home/wrestlingdb/.env
ExecStart=/home/wrestlingdb/app/venv/bin/celery -A owdb_django worker \
  --loglevel=info --concurrency=2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/wrestlingdb-beat.service`**
```ini
[Unit]
Description=OWDB Celery beat (schedule the 3 agents)
After=network.target wrestlingdb-celery.service

[Service]
Type=simple
User=wrestlingdb
Group=wrestlingdb
WorkingDirectory=/home/wrestlingdb/app
EnvironmentFile=/home/wrestlingdb/.env
ExecStart=/home/wrestlingdb/app/venv/bin/celery -A owdb_django beat \
  --loglevel=info \
  --schedule=/home/wrestlingdb/celerybeat-schedule
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable them:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now wrestlingdb-web wrestlingdb-celery wrestlingdb-beat
sudo systemctl status wrestlingdb-web
```

At this point you should see gunicorn listening on `127.0.0.1:8000`. Test
locally on the NUC: `curl http://127.0.0.1:8000/` should return the
homepage HTML.

## Step 4 — Cloudflare Tunnel

Run on the NUC. Cloudflare provides a managed daemon — no port forwarding,
no inbound firewall rules.

```bash
# 1. Install cloudflared
curl -L --output cloudflared.deb \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# 2. Authenticate to Cloudflare (browser opens for your CF account)
cloudflared tunnel login

# 3. Create the tunnel
cloudflared tunnel create wrestlingdb

# 4. Route DNS — this CREATES the CNAME wrestlingdb.org → <tunnel>.cfargotunnel.com
#    automatically, no manual DNS work needed.
cloudflared tunnel route dns wrestlingdb wrestlingdb.org
cloudflared tunnel route dns wrestlingdb www.wrestlingdb.org

# 5. Config file
sudo mkdir -p /etc/cloudflared
sudo tee /etc/cloudflared/config.yml > /dev/null <<'EOF'
tunnel: wrestlingdb
credentials-file: /root/.cloudflared/<TUNNEL-UUID>.json
ingress:
  - hostname: wrestlingdb.org
    service: http://127.0.0.1:8000
  - hostname: www.wrestlingdb.org
    service: http://127.0.0.1:8000
  - service: http_status:404
EOF

# 6. Install as a service
sudo cloudflared service install
sudo systemctl enable --now cloudflared
sudo systemctl status cloudflared
```

The `cloudflared tunnel route dns` commands take care of removing any
stale records and writing the correct CNAME automatically. After step 4
finishes, `https://wrestlingdb.org` should serve the Django app over
Cloudflare's edge.

## Step 5 — Verify

```bash
# From your laptop (not the NUC):
curl -I https://wrestlingdb.org
# Expect: 200, server: cloudflare, NO certificate-mismatch warning

# Confirm the IP is no longer 137.184.7.163:
dig +short wrestlingdb.org
# Expect: a Cloudflare IP (104.21.x.x or 172.67.x.x)

# Confirm images still serve via R2:
curl -I https://images.wrestlingdb.org/wrestlers/79/...jpg
# Expect: 200, cf-cache-status header present
```

## What you get out of the box

Once steps 1-5 complete:

- **`https://wrestlingdb.org`** serves the live Django site
- **`https://images.wrestlingdb.org`** continues serving via R2 CDN (unchanged)
- **JR / Al / Earl** run on the existing Celery beat schedule (JR every
  30 min, Al every 30 min, Earl every 6 hours). All three agents continue
  growing the database 24/7 from the NUC.
- **The site is hidden behind Cloudflare's edge** — your NUC's public IP
  is never exposed.

## Future migration path

When the NUC stops being adequate:

1. **First sign:** gunicorn 95th-percentile request time climbs past 500 ms,
   or you notice multi-second waits on the wrestler-detail pages
2. **First move:** add caching middleware (Django's per-view cache, or
   Cloudflare Page Rules with bypass for `/admin/`). Free, big lift
3. **Second move:** stand up a $6/mo Hetzner / DigitalOcean droplet,
   pg_dump the Postgres, rsync the repo. The systemd + cloudflared
   config moves over unchanged. The tunnel's hostname stays the same,
   so DNS doesn't need touching
4. **Third move:** managed Postgres (Neon free tier, or DigitalOcean
   $15/mo), separate worker droplets if agent throughput needs it

## Things I haven't included

- **Backups.** The Postgres + R2 + media data should be backed up; not
  doing so for the first month is a calculated risk while traffic is zero
- **Monitoring / alerting.** Add Sentry (free tier covers low-traffic
  sites) once you have any users
- **Email (SMTP).** OWDB doesn't send transactional email yet other than
  password-reset; Postmark / Resend free tiers cover the first 100
  emails/day at $0 when needed
- **CI/CD.** The README's `ssh + git pull + systemctl restart` flow still
  works. Add a GitHub Action later if you start shipping multiple times
  per day
