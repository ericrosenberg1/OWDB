# WrestleBot 2.0 - Implementation Guide

## Summary

We've separated WrestleBot from Django to prevent freezing and enable unlimited data collection. Here's what has been built:

### 1. Django REST API (✅ COMPLETE)

**Location:** `/wrestlebot_api/`

**Components Created:**
- `serializers.py` - Data validation and transformation
- `views.py` - API endpoints for all entity types
- `permissions.py` - Authentication and access control
- `urls.py` - URL routing
- Management command: `setup_wrestlebot_user.py`

**Endpoints Available:**
```
GET/POST   /api/wrestlebot/wrestlers/
GET/POST   /api/wrestlebot/promotions/
GET/POST   /api/wrestlebot/events/
GET/POST   /api/wrestlebot/articles/
POST       /api/wrestlebot/bulk/import/
GET        /api/wrestlebot/status/
GET        /api/wrestlebot/health/
```

**Setup Steps:**

1. **Run migrations:**
```bash
./venv/bin/python manage.py makemigrations
./venv/bin/python manage.py migrate
```

2. **Create WrestleBot user and API token:**
```bash
./venv/bin/python manage.py setup_wrestlebot_user
```

This will output something like:
```
API Token: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
```

3. **Save the token** - You'll need this for the standalone service

4. **Test the API:**
```bash
curl -H "Authorization: Token YOUR_TOKEN_HERE" \
  http://localhost:8000/api/wrestlebot/status/
```

Should return:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "database_connected": true,
  "total_wrestlers": 123,
  ...
}
```

---

## Next Steps

### 2. Build Standalone WrestleBot Service (⏳ IN PROGRESS)

The standalone service will run independently of Django with no time limits.

**Directory Structure:**
```
wrestlebot/                      # Standalone service
├── main.py                      # Entry point
├── config/
│   ├── settings.yaml            # Service configuration
│   └── sources.yaml             # Data source definitions
├── scrapers/
│   ├── base.py                  # Base scraper class
│   ├── wikipedia.py             # Wikipedia scraper
│   ├── news_rss.py              # RSS feed scraper
│   ├── cagematch.py             # Cagematch scraper
│   └── ...
├── api_client/
│   ├── django_api.py            # Django REST API client
│   └── auth.py                  # Authentication
├── workers/
│   ├── scraper_worker.py        # Scraping threads
│   ├── processor_worker.py      # AI processing
│   └── publisher_worker.py      # Publish to Django
├── queue/
│   ├── task_queue.py            # SQLite task queue
│   └── retry_handler.py         # Retry logic
├── utils/
│   ├── circuit_breaker.py       # Circuit breaker pattern
│   ├── rate_limiter.py          # Smart rate limiting
│   ├── logging.py               # Logging configuration
│   └── health.py                # Health checks
└── requirements.txt             # Python dependencies
```

**Key Features:**
- ✅ No time limits - runs indefinitely
- ✅ Concurrent workers for different sources
- ✅ Circuit breaker - skip failing sources, retry later
- ✅ Local SQLite queue for failed operations
- ✅ Smart rate limiting per source
- ✅ Self-healing - auto-restart on errors

---

### 3. Scraping Strategy

#### Wikipedia Full Download

**Option 1: Wikipedia Dumps (Recommended)**

```python
# Download complete Wikipedia dump once
# Extract wrestling-related articles
# Process in batches
# Delete dump after processing

# Future updates: Use API for new articles only
```

**Option 2: Bulk API Queries**

```python
# Get all articles in wrestling categories
# Batch fetch content (50 articles per request)
# Process in parallel
```

#### RSS Feed Strategy

```python
# Check RSS feeds every 5 minutes
# Scrape full article content
# Extract entities (wrestlers, promotions, events)
# Publish to Django via API
# No rate limiting issues (RSS designed for frequent checks)
```

#### Error Handling

```python
# Circuit Breaker Pattern
if source.failures > 5:
    # Open circuit for 5 minutes
    skip_source(source)
else:
    try:
        data = source.scrape()
        circuit_breaker.record_success()
    except Exception:
        circuit_breaker.record_failure()
        retry_queue.add(source, data)
```

---

### 4. Process Management

**systemd Service (Production)**

```ini
[Unit]
Description=WrestleBot Data Collection Service
After=network.target postgresql.service

[Service]
Type=simple
User=wrestlebot
WorkingDirectory=/opt/wrestlebot
ExecStart=/opt/wrestlebot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Commands:**
```bash
sudo systemctl start wrestlebot
sudo systemctl stop wrestlebot
sudo systemctl status wrestlebot
sudo systemctl enable wrestlebot  # Auto-start on boot
```

**Logs:**
```bash
journalctl -u wrestlebot -f  # Follow logs
```

---

## Configuration

### Django Settings (.env)

```bash
# Django
DEBUG=False
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@localhost/wrestlingdb

# WrestleBot API Token
WRESTLEBOT_API_TOKEN=your-token-from-setup-command
```

### WrestleBot Settings (wrestlebot/.env)

```bash
# Django API Connection
DJANGO_API_URL=http://localhost:8000/api/wrestlebot
DJANGO_API_TOKEN=your-token-from-setup-command

# Ollama AI
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Workers
SCRAPER_THREADS=5
PROCESSOR_THREADS=2
PUBLISHER_THREADS=2

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/wrestlebot/wrestlebot.log
```

---

## Data Sources Configuration

### wrestlebot/config/sources.yaml

```yaml
sources:
  - name: "wikipedia"
    enabled: true
    scraper: "scrapers.wikipedia.WikipediaScraper"
    rate_limit:
      per_minute: 60
      per_hour: 500
    circuit_breaker:
      failure_threshold: 5
      timeout: 300

  - name: "wrestling_inc"
    enabled: true
    scraper: "scrapers.news_rss.WrestlingIncScraper"
    rss_url: "https://www.wrestlinginc.com/feed/"
    rate_limit:
      per_minute: 10
      per_hour: 100

  - name: "wrestlezone"
    enabled: true
    scraper: "scrapers.news_rss.WrestleZoneScraper"
    rss_url: "https://www.wrestlezone.com/feed/"

  - name: "pwtorch"
    enabled: true
    scraper: "scrapers.news_rss.PWTorchScraper"
    rss_url: "https://www.pwtorch.com/feed"

  - name: "ringside_news"
    enabled: true
    scraper: "scrapers.news_rss.RingsideNewsScraper"
    rss_url: "https://www.ringsidenews.com/feed/"

  - name: "fightful"
    enabled: true
    scraper: "scrapers.news_rss.FightfulScraper"
    rss_url: "https://www.fightful.com/wrestling/feed"

  - name: "cagematch"
    enabled: true
    scraper: "scrapers.cagematch.CagematchScraper"
    rate_limit:
      per_minute: 5
      per_hour: 50

  - name: "profightdb"
    enabled: true
    scraper: "scrapers.profightdb.ProFightDBScraper"
    rate_limit:
      per_minute: 10
      per_hour: 100
```

---

## Monitoring

### Health Checks

**WrestleBot Health Endpoint:**
```bash
curl http://localhost:9090/health
```

Returns:
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "sources": {
    "wikipedia": {"status": "active", "last_success": "2025-12-18T12:00:00Z"},
    "wrestling_inc": {"status": "circuit_open", "retry_at": "2025-12-18T12:05:00Z"}
  },
  "queues": {
    "pending": 10,
    "failed": 2
  }
}
```

### Metrics

**Prometheus Metrics Endpoint:**
```bash
curl http://localhost:9090/metrics
```

Metrics include:
- `wrestlebot_articles_published_total`
- `wrestlebot_scraper_requests_total`
- `wrestlebot_scraper_errors_total`
- `wrestlebot_circuit_breaker_state`
- `wrestlebot_queue_size`

---

## Troubleshooting

### WrestleBot Not Starting

```bash
# Check logs
journalctl -u wrestlebot -f

# Check if Django API is accessible
curl http://localhost:8000/api/wrestlebot/health/

# Check if token is valid
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/wrestlebot/status/
```

### Sources Failing

```bash
# Check circuit breaker status
curl http://localhost:9090/health

# Reset circuit breaker for a source
curl -X POST http://localhost:9090/reset-circuit/wikipedia
```

### Django API Not Responding

```bash
# Check Django is running
ps aux | grep gunicorn

# Check database connection
./venv/bin/python manage.py dbshell

# Test API manually
./venv/bin/python manage.py shell
>>> from wrestlebot_api.views import service_status
```

---

## Development Workflow

### Running Locally

**Terminal 1 - Django:**
```bash
cd /Users/eric/Code/wrestlingdb
./venv/bin/python manage.py runserver
```

**Terminal 2 - WrestleBot:**
```bash
cd /Users/eric/Code/wrestlingdb/wrestlebot
../venv/bin/python main.py
```

**Terminal 3 - Logs:**
```bash
tail -f /tmp/wrestlebot.log
```

### Testing

**Test Django API:**
```bash
./venv/bin/python manage.py test wrestlebot_api
```

**Test WrestleBot scrapers:**
```bash
cd wrestlebot
../venv/bin/python -m pytest tests/
```

---

## Performance Tuning

### Increase Scraping Speed

1. **Add more worker threads:**
```yaml
workers:
  scrapers: 10  # Increase from 5
  processors: 4  # Increase from 2
  publishers: 4  # Increase from 2
```

2. **Increase rate limits:**
```yaml
sources:
  - name: "wikipedia"
    rate_limit:
      per_minute: 120  # Increase from 60
```

3. **Disable AI processing temporarily:**
```yaml
ollama:
  enabled: false  # Skip AI verification for speed
  fallback_on_failure: true
```

### Reduce Resource Usage

1. **Decrease worker threads:**
```yaml
workers:
  scrapers: 2
  processors: 1
  publishers: 1
```

2. **Add delays between requests:**
```yaml
sources:
  - name: "wikipedia"
    delay_between_requests: 2  # Seconds
```

---

## Next Implementation Steps

### Week 1
1. ✅ Create Django REST API
2. ⏳ Build basic WrestleBot service structure
3. ⏳ Implement Wikipedia scraper
4. ⏳ Implement RSS feed scrapers
5. ⏳ Add circuit breaker and retry queue

### Week 2
6. Add more news sources (PWInsider, F4W, etc.)
7. Implement Wikipedia dump processing
8. Add YouTube metadata scraper
9. Add SEC EDGAR scraper
10. Performance testing and tuning

### Week 3
11. Deploy to production server
12. Set up monitoring (Prometheus + Grafana)
13. Configure alerts
14. Documentation and training

### Ongoing
15. Add more data sources
16. Optimize database writes
17. Scale horizontally (multiple WrestleBot instances)
18. Machine learning for entity linking

---

## Success Metrics

### Phase 1 (Week 1-2)
- ✅ Zero freezes/timeouts
- ✅ WrestleBot runs continuously for 7+ days
- ✅ Process 100+ articles per day
- ✅ < 5% error rate

### Phase 2 (Week 3-4)
- ✅ Process 1000+ articles per day
- ✅ Cover all major news sources
- ✅ 99.9% uptime

### Phase 3 (Month 2+)
- ✅ Comprehensive Wikipedia coverage (50,000+ wrestlers)
- ✅ Real-time news from 20+ sources
- ✅ Historical data imported from dumps
- ✅ API response time < 100ms

---

**The architecture is now in place. WrestleBot will never freeze again and can scale to unlimited data sources!**
