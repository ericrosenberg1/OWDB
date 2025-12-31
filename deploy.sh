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
DEPLOY_PATH="/opt/owdb"
SSH_OPTS="-o BatchMode=yes -o ConnectTimeout=30 -o RemoteCommand=none"

echo "Target server: $SERVER_USER@$SERVER_HOST"
echo "Deploy path: $DEPLOY_PATH"
echo ""

# Step 1: Pull latest code on server
echo "[1/5] Pulling latest code from GitHub..."
ssh $SSH_OPTS $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /opt/owdb
git pull origin main
ENDSSH

# Step 2: Rebuild Docker containers
echo "[2/5] Rebuilding Docker containers..."
ssh $SSH_OPTS $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /opt/owdb
sudo docker compose build --no-cache
ENDSSH

# Step 3: Run Django migrations
echo "[3/5] Running Django migrations..."
ssh $SSH_OPTS $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /opt/owdb
sudo docker compose up -d
sleep 5
sudo docker compose exec -T web python manage.py migrate
ENDSSH

# Step 4: Collect static files
echo "[4/5] Collecting static files..."
ssh $SSH_OPTS $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /opt/owdb
sudo docker compose exec -T web python manage.py collectstatic --noinput
ENDSSH

# Step 5: Restart services
echo "[5/5] Restarting services..."
ssh $SSH_OPTS $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /opt/owdb
sudo docker compose restart
sleep 5
sudo docker compose ps
ENDSSH

echo ""
echo "================================"
echo "Deployment Complete!"
echo "================================"
echo ""
echo "Services status:"
echo "  Docker: sudo docker compose ps (in /opt/owdb)"
echo ""
echo "View logs:"
echo "  Web: sudo docker compose logs -f web"
echo "  Celery: sudo docker compose logs -f celery"
echo ""
echo "Test the site:"
echo "  https://wrestlingdb.org"
echo ""
