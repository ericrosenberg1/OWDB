#!/bin/bash
#
# Deployment script for WrestlingDB
#

set -e  # Exit on error

echo "================================"
echo "WrestlingDB Deployment Script"
echo "================================"
echo ""

# Configuration
SERVER_USER="eric"
SERVER_HOST="137.184.7.163"
DEPLOY_PATH="/home/wrestlingdb"
VENV_PATH="$DEPLOY_PATH/venv"
SSH_OPTS="-o BatchMode=yes -o ConnectTimeout=30 -o RemoteCommand=none"

echo "Target server: $SERVER_USER@$SERVER_HOST"
echo "Deploy path: $DEPLOY_PATH"
echo ""

# Step 1: Pull latest code on server
echo "[1/5] Pulling latest code from GitHub..."
ssh $SSH_OPTS $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /home/wrestlingdb
git pull origin main
ENDSSH

# Step 2: Install Python dependencies
echo "[2/5] Installing Python dependencies..."
ssh $SSH_OPTS $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /home/wrestlingdb
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt
ENDSSH

# Step 3: Run Django migrations
echo "[3/5] Running Django migrations..."
ssh $SSH_OPTS $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /home/wrestlingdb
./venv/bin/python manage.py migrate
ENDSSH

# Step 4: Collect static files
echo "[4/5] Collecting static files..."
ssh $SSH_OPTS $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /home/wrestlingdb
./venv/bin/python manage.py collectstatic --noinput
ENDSSH

# Step 5: Restart Django service
echo "[5/5] Restarting Django service..."
ssh $SSH_OPTS $SERVER_USER@$SERVER_HOST << 'ENDSSH'
sudo systemctl restart wrestlingdb
sleep 2
sudo systemctl status wrestlingdb --no-pager
ENDSSH

echo ""
echo "================================"
echo "Deployment Complete!"
echo "================================"
echo ""
echo "Services status:"
echo "  Django: systemctl status wrestlingdb"
echo ""
echo "View logs:"
echo "  Django: journalctl -u wrestlingdb -f"
echo ""
echo "Test the site:"
echo "  https://wrestlingdb.org"
echo ""
