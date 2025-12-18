# Manual Deployment Steps for WrestleBot 2.0

Since automated deployment requires SSH keys, follow these manual steps:

## Step 1: SSH to Server

```bash
ssh root@wrestlingdb.org
```

## Step 2: Pull Latest Code

```bash
cd /home/wrestlingdb
git pull origin main
```

## Step 3: Install Dependencies

```bash
# Upgrade pip
./venv/bin/python -m pip install --upgrade pip

# Install Django dependencies
./venv/bin/python -m pip install djangorestframework

# Install WrestleBot dependencies
./venv/bin/python -m pip install -r wrestlebot/requirements.txt
```

## Step 4: Run Migrations

```bash
./venv/bin/python manage.py migrate
```

## Step 5: Collect Static Files

```bash
./venv/bin/python manage.py collectstatic --noinput
```

## Step 6: Set Up WrestleBot API User

```bash
./venv/bin/python manage.py setup_wrestlebot_user
```

**IMPORTANT:** Copy the API token that is displayed. You'll need it in the next step.

Example output:
```
API Token: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
```

## Step 7: Create WrestleBot .env File

```bash
cd /home/wrestlingdb/wrestlebot

# Create .env file
nano .env
```

Paste this content (replace YOUR_TOKEN with the token from Step 6):

```bash
# WrestleBot Environment Configuration

# Django API Configuration
DJANGO_API_URL=https://wrestlingdb.org/api/wrestlebot
WRESTLEBOT_API_TOKEN=YOUR_TOKEN_HERE

# Ollama AI Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/wrestlebot/wrestlebot.log

# Environment
ENVIRONMENT=production
```

Save and exit (Ctrl+X, Y, Enter)

Set proper permissions:
```bash
chmod 600 /home/wrestlingdb/wrestlebot/.env
chown www-data:www-data /home/wrestlingdb/wrestlebot/.env
```

## Step 8: Create Log and Data Directories

```bash
# Create log directory
sudo mkdir -p /var/log/wrestlebot
sudo chown www-data:www-data /var/log/wrestlebot

# Create data directory for queue database
sudo mkdir -p /var/lib/wrestlebot
sudo chown www-data:www-data /var/lib/wrestlebot
```

## Step 9: Install WrestleBot systemd Service

```bash
# Copy service file
sudo cp /home/wrestlingdb/wrestlebot/wrestlebot.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable wrestlebot
```

## Step 10: Restart Django Service

```bash
sudo systemctl restart wrestlingdb
sleep 2
sudo systemctl status wrestlingdb
```

You should see:
```
● wrestlingdb.service - WrestlingDB Django Application
   Loaded: loaded
   Active: active (running)
```

## Step 11: Start WrestleBot Service

```bash
sudo systemctl start wrestlebot
sleep 2
sudo systemctl status wrestlebot
```

You should see:
```
● wrestlebot.service - WrestleBot Data Collection Service
   Loaded: loaded
   Active: active (running)
```

## Step 12: Verify Everything is Working

### Check Django API

```bash
curl https://wrestlingdb.org/api/wrestlebot/health/
```

Should return:
```json
{"status":"ok","timestamp":"2025-12-18T..."}
```

### Check WrestleBot Logs

```bash
sudo journalctl -u wrestlebot -n 50
```

You should see:
```
WrestleBot Service v2.0.0
Django API: https://wrestlingdb.org/api/wrestlebot
API health check: OK
Service initialized successfully
Starting main service loop...
```

### Check Both Services are Running

```bash
sudo systemctl status wrestlingdb wrestlebot
```

Both should show `Active: active (running)`

## Step 13: Monitor Logs

Keep an eye on both services:

```bash
# In one terminal:
sudo journalctl -u wrestlingdb -f

# In another terminal:
sudo journalctl -u wrestlebot -f
```

## Troubleshooting

### WrestleBot Won't Start

```bash
# Check detailed status
sudo systemctl status wrestlebot -l

# Check logs
sudo journalctl -u wrestlebot -n 100

# Common issues:
# 1. Missing .env file
ls -la /home/wrestlingdb/wrestlebot/.env

# 2. Wrong permissions
sudo chown www-data:www-data /home/wrestlingdb/wrestlebot/.env

# 3. Invalid API token
# Re-run: ./venv/bin/python manage.py setup_wrestlebot_user
```

### Django API Not Accessible

```bash
# Check Django is running
sudo systemctl status wrestlingdb

# Test locally from server
curl http://localhost:8000/api/wrestlebot/health/

# Check Nginx configuration
sudo nginx -t
sudo systemctl reload nginx
```

### API Authentication Failed

```bash
# Get the correct token
cd /home/wrestlingdb
./venv/bin/python manage.py shell

# In Python shell:
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.get(username='wrestlebot')
token, _ = Token.objects.get_or_create(user=user)
print(f"Token: {token.key}")

# Update .env with correct token
nano /home/wrestlingdb/wrestlebot/.env
```

## Restarting Services

```bash
# Restart Django only
sudo systemctl restart wrestlingdb

# Restart WrestleBot only
sudo systemctl restart wrestlebot

# Restart both
sudo systemctl restart wrestlingdb wrestlebot

# View status
sudo systemctl status wrestlingdb wrestlebot
```

## Stopping Services

```bash
# Stop WrestleBot
sudo systemctl stop wrestlebot

# Stop Django
sudo systemctl stop wrestlingdb

# Stop both
sudo systemctl stop wrestlingdb wrestlebot
```

## Success Indicators

✅ Django shows: `Active: active (running)`
✅ WrestleBot shows: `Active: active (running)`
✅ API health check returns: `{"status":"ok"}`
✅ WrestleBot logs show: "API health check: OK"
✅ No errors in journalctl logs
✅ Website accessible at https://wrestlingdb.org

## Next Steps After Deployment

1. Monitor logs for the first hour
2. Verify WrestleBot is making API calls
3. Check database for new entries
4. Set up monitoring/alerts (optional)
5. Begin adding actual scraping logic to WrestleBot

---

**Deployment complete! WrestleBot is now running independently of Django.**
