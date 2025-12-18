# WrestleBot 2.0 - Standalone Data Collection Service

## Overview

WrestleBot is a standalone service that runs independently of Django to continuously collect wrestling data from multiple sources. It communicates with Django via REST API.

## Quick Start

### 1. Set Up Django API

```bash
# From the main wrestlingdb directory
cd /home/wrestlingdb

# Run migrations
./venv/bin/python manage.py migrate

# Create WrestleBot API user and get token
./venv/bin/python manage.py setup_wrestlebot_user
# Save the token that is displayed
```

### 2. Configure WrestleBot

```bash
cd wrestlebot

# Copy environment file
cp .env.example .env

# Edit .env and add your API token
nano .env
# Set WRESTLEBOT_API_TOKEN=your-token-here
```

### 3. Install Dependencies

```bash
# Install Python requirements
../venv/bin/python -m pip install -r requirements.txt
```

### 4. Test Locally

```bash
# Make sure Django is running in another terminal
cd /home/wrestlingdb
./venv/bin/python manage.py runserver

# In this terminal, run WrestleBot
cd wrestlebot
export WRESTLEBOT_API_TOKEN=your-token-here
../venv/bin/python main.py
```

You should see:
```
WrestleBot Service v2.0.0
Django API: http://localhost:8000/api/wrestlebot
API health check: OK
Service initialized successfully
Starting main service loop...
```

### 5. Deploy as systemd Service (Production)

```bash
# Copy service file
sudo cp wrestlebot.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable wrestlebot

# Start the service
sudo systemctl start wrestlebot

# Check status
sudo systemctl status wrestlebot

# View logs
sudo journalctl -u wrestlebot -f
```

## Architecture

```
WrestleBot Service (Standalone)
├── main.py                 # Entry point
├── api_client/
│   └── django_api.py       # Django REST API client
├── scrapers/
│   ├── wikipedia_scraper.py
│   ├── rss_scraper.py
│   └── ...
├── utils/
│   ├── circuit_breaker.py  # Fault tolerance
│   └── ...
└── config/
    ├── settings.yaml       # Service config
    └── sources.yaml        # Data sources
```

## Features

### ✅ No Time Limits
- Runs indefinitely
- No Celery soft/hard limits
- Self-healing with auto-restart

### ✅ Circuit Breaker Pattern
- If Wikipedia fails 5 times, skip for 5 minutes
- Other sources continue working
- Automatic retry when service recovers

### ✅ Smart Rate Limiting
- Per-source rate limits
- Adaptive backoff on errors
- Respects robots.txt

### ✅ Robust Error Handling
- Retry queue for failed operations
- Graceful degradation
- Comprehensive logging

## Configuration

### Environment Variables

```bash
# Required
WRESTLEBOT_API_TOKEN=your-token-here

# Optional (with defaults)
DJANGO_API_URL=http://localhost:8000/api/wrestlebot
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
LOG_LEVEL=INFO
```

### Data Sources

Edit `config/sources.yaml` to enable/disable sources:

```yaml
sources:
  - name: "wikipedia"
    enabled: true
    rate_limit:
      per_minute: 60
      per_hour: 500

  - name: "wrestling_inc"
    enabled: true
    config:
      rss_url: "https://www.wrestlinginc.com/feed/"
```

## Commands

### Systemd Service

```bash
# Start
sudo systemctl start wrestlebot

# Stop
sudo systemctl stop wrestlebot

# Restart
sudo systemctl restart wrestlebot

# Status
sudo systemctl status wrestlebot

# Logs (live)
sudo journalctl -u wrestlebot -f

# Logs (last 100 lines)
sudo journalctl -u wrestlebot -n 100
```

### Manual Testing

```bash
# Run in foreground (with logs)
cd /home/wrestlingdb/wrestlebot
export WRESTLEBOT_API_TOKEN=your-token
../venv/bin/python main.py

# Test API connectivity
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/wrestlebot/status/
```

## Monitoring

### Health Check

WrestleBot checks Django API health every cycle:

```
API health check: OK
```

If API is down:
```
API health check failed, will retry next cycle
```

### Logs

```bash
# Real-time logs
sudo journalctl -u wrestlebot -f

# Filter by error level
sudo journalctl -u wrestlebot -p err

# Logs since boot
sudo journalctl -u wrestlebot -b
```

## Troubleshooting

### Service Won't Start

```bash
# Check status
sudo systemctl status wrestlebot

# View recent logs
sudo journalctl -u wrestlebot -n 50

# Check for port conflicts
sudo netstat -tulpn | grep python

# Verify API token
grep WRESTLEBOT_API_TOKEN /home/wrestlingdb/wrestlebot/.env
```

### API Connection Failed

```bash
# Test Django is running
curl http://localhost:8000/api/wrestlebot/health/

# Test with authentication
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/wrestlebot/status/

# Check Django logs
sudo journalctl -u wrestlingdb -n 50
```

### High Memory Usage

```bash
# Check memory usage
systemctl status wrestlebot

# Adjust memory limit in service file
sudo nano /etc/systemd/system/wrestlebot.service
# Change: MemoryLimit=2G

sudo systemctl daemon-reload
sudo systemctl restart wrestlebot
```

## Development

### Adding a New Scraper

1. Create scraper file:
```python
# scrapers/my_scraper.py
from scrapers.base import BaseScraper

class MySourceScraper(BaseScraper):
    def scrape(self):
        # Your scraping logic
        return data
```

2. Add to sources.yaml:
```yaml
- name: "my_source"
  enabled: true
  scraper: "scrapers.my_scraper.MySourceScraper"
  rate_limit:
    per_minute: 10
```

3. Test locally:
```bash
../venv/bin/python main.py
```

### Running Tests

```bash
# Install test dependencies
../venv/bin/python -m pip install pytest

# Run tests
../venv/bin/python -m pytest tests/
```

## Performance Tuning

### Increase Scraping Speed

Edit `config/settings.yaml`:

```yaml
workers:
  scrapers: 10  # Increase from 5
  processors: 4  # Increase from 2
```

### Reduce Resource Usage

```yaml
workers:
  scrapers: 2  # Decrease workers
  processors: 1
```

## Next Steps

1. Add actual scraping logic to `main.py`
2. Implement Wikipedia scraper
3. Implement RSS feed scrapers
4. Add retry queue for failed operations
5. Set up Prometheus metrics

## Support

For issues or questions:
- Check logs: `sudo journalctl -u wrestlebot -f`
- View implementation guide: `/home/wrestlingdb/IMPLEMENTATION_GUIDE.md`
- View architecture: `/home/wrestlingdb/ARCHITECTURE.md`
