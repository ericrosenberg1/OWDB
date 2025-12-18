#!/bin/bash
#
# Deployment script for WrestlingDB + WrestleBot
#
# This script deploys the separated architecture to the server.
#

set -e  # Exit on error

echo "================================"
echo "WrestlingDB Deployment Script"
echo "================================"
echo ""

# Configuration
SERVER_USER="root"
SERVER_HOST="wrestlingdb.org"
DEPLOY_PATH="/home/wrestlingdb"
VENV_PATH="$DEPLOY_PATH/venv"

echo "Target server: $SERVER_USER@$SERVER_HOST"
echo "Deploy path: $DEPLOY_PATH"
echo ""

# Step 1: Pull latest code on server
echo "[1/8] Pulling latest code from GitHub..."
ssh $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /home/wrestlingdb
git pull origin main
ENDSSH

# Step 2: Install Python dependencies
echo "[2/8] Installing Python dependencies..."
ssh $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /home/wrestlingdb
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python -m pip install -r wrestlebot/requirements.txt
ENDSSH

# Step 3: Run Django migrations
echo "[3/8] Running Django migrations..."
ssh $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /home/wrestlingdb
./venv/bin/python manage.py migrate
ENDSSH

# Step 4: Collect static files
echo "[4/8] Collecting static files..."
ssh $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /home/wrestlingdb
./venv/bin/python manage.py collectstatic --noinput
ENDSSH

# Step 5: Set up WrestleBot user (if not exists)
echo "[5/8] Setting up WrestleBot API user..."
ssh $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /home/wrestlingdb
./venv/bin/python manage.py setup_wrestlebot_user || true
ENDSSH

# Step 6: Install WrestleBot systemd service
echo "[6/8] Installing WrestleBot systemd service..."
ssh $SERVER_USER@$SERVER_HOST << 'ENDSSH'
# Copy service file
sudo cp /home/wrestlingdb/wrestlebot/wrestlebot.service /etc/systemd/system/

# Create log directory
sudo mkdir -p /var/log/wrestlebot
sudo chown www-data:www-data /var/log/wrestlebot

# Create lib directory for queue database
sudo mkdir -p /var/lib/wrestlebot
sudo chown www-data:www-data /var/lib/wrestlebot

# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable wrestlebot
ENDSSH

# Step 7: Restart Django service
echo "[7/8] Restarting Django service..."
ssh $SERVER_USER@$SERVER_HOST << 'ENDSSH'
sudo systemctl restart wrestlingdb
sleep 2
sudo systemctl status wrestlingdb --no-pager
ENDSSH

# Step 8: Restart WrestleBot service
echo "[8/8] Restarting WrestleBot service..."
ssh $SERVER_USER@$SERVER_HOST << 'ENDSSH'
sudo systemctl restart wrestlebot
sleep 2
sudo systemctl status wrestlebot --no-pager
ENDSSH

echo ""
echo "================================"
echo "Deployment Complete!"
echo "================================"
echo ""
echo "Services status:"
echo "  Django:     systemctl status wrestlingdb"
echo "  WrestleBot: systemctl status wrestlebot"
echo ""
echo "View logs:"
echo "  Django:     journalctl -u wrestlingdb -f"
echo "  WrestleBot: journalctl -u wrestlebot -f"
echo ""
echo "Test the site:"
echo "  https://wrestlingdb.org"
echo ""
echo "Test WrestleBot API:"
echo "  curl https://wrestlingdb.org/api/wrestlebot/health/"
echo ""
