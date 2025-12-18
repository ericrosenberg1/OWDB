# WrestlingDB Architecture - Separated Services

## Overview

This document outlines the new architecture that separates WrestleBot data collection from the Django frontend, ensuring continuous operation without freezing.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND LAYER                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Django Web Application (OWDB)                │  │
│  │  - User-facing website                                    │  │
│  │  - Read-only database access for frontend                 │  │
│  │  - REST API for WrestleBot                                │  │
│  │  - Static file serving                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               ▲
                               │ HTTP REST API
                               │ (Create/Update/Post articles)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA COLLECTION LAYER                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              WrestleBot Service (Standalone)              │  │
│  │  - Runs independently of Django                           │  │
│  │  - No time limits or freezing                             │  │
│  │  - Multi-threaded scraping                                │  │
│  │  - Connects to Django via REST API                        │  │
│  │  - Own process supervisor (systemd/supervisor)            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐  │
│  │   Wikipedia    │  │   Cagematch    │  │   ProFightDB    │  │
│  │   Scraper      │  │   Scraper      │  │    Scraper      │  │
│  │   (Thread 1)   │  │   (Thread 2)   │  │   (Thread 3)    │  │
│  └────────────────┘  └────────────────┘  └─────────────────┘  │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐  │
│  │   RSS Feeds    │  │   Ollama AI    │  │  Error Handler  │  │
│  │   (Thread 4)   │  │   Processor    │  │  & Retry Queue  │  │
│  └────────────────┘  └────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DATABASE LAYER                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              PostgreSQL Database (Shared)                 │  │
│  │  - Shared by both Django and WrestleBot                   │  │
│  │  - Django: Read-only for frontend queries                 │  │
│  │  - WrestleBot: Write access via REST API only             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Django Web Application (OWDB Frontend)

**Purpose:** Serve the public-facing wrestling database website

**Responsibilities:**
- Display wrestler profiles, events, matches, articles
- Provide search and browse functionality
- Expose REST API for WrestleBot to create/update content
- Handle user authentication (if applicable)
- Serve static assets

**Technology Stack:**
- Django 5.x
- Django REST Framework for API
- PostgreSQL for database
- Gunicorn/uWSGI for WSGI server
- Nginx for reverse proxy

**Key Features:**
- **Read-optimized:** Frontend only reads from database
- **Token Authentication:** WrestleBot uses secure API token
- **Rate Limiting:** API endpoints have sensible rate limits
- **Monitoring:** Health checks and metrics

---

### 2. WrestleBot Service (Standalone Python Service)

**Purpose:** Continuously collect, process, and publish wrestling data

**Responsibilities:**
- Scrape data from all sources (Wikipedia, news sites, databases)
- Process data with AI (Ollama)
- Submit articles to Django via REST API
- Handle errors and retry failed operations
- Never stop running (self-healing)

**Technology Stack:**
- Python 3.14
- AsyncIO for concurrent operations
- Requests/httpx for HTTP
- BeautifulSoup/lxml for parsing
- SQLite for local queue/cache
- systemd or supervisord for process management

**Key Features:**
- **No time limits:** Runs indefinitely
- **Concurrent workers:** Multiple threads for different sources
- **Circuit breaker:** Skip failing sources, retry later
- **Local queue:** Failed operations stored locally and retried
- **Graceful degradation:** If one source fails, others continue
- **Progress tracking:** Logs and metrics for monitoring

---

### 3. Django REST API for WrestleBot

**Endpoints:**

```python
# Authentication
POST /api/wrestlebot/auth/
  - Exchange token for session

# Article Management
POST /api/wrestlebot/articles/
  - Create new article
  - Body: {title, slug, content, category, tags[], author}
  - Returns: {id, url, created_at}

PUT /api/wrestlebot/articles/{id}/
  - Update existing article
  - Body: {content, updated_reason}
  - Returns: {id, url, updated_at}

# Entity Management
POST /api/wrestlebot/wrestlers/
  - Create or update wrestler
  - Body: {name, real_name, debut_year, ...}
  - Returns: {id, url, created}

POST /api/wrestlebot/promotions/
POST /api/wrestlebot/events/
POST /api/wrestlebot/matches/
  - Similar patterns for other entities

# Health & Status
GET /api/wrestlebot/status/
  - Returns service health, rate limits, etc.

# Bulk Operations
POST /api/wrestlebot/bulk/import/
  - Import multiple entities at once
  - Batch processing for efficiency
```

**Security:**
- Token-based authentication
- IP whitelist (localhost or VPN only)
- Rate limiting (high limits for bot)
- Input validation
- CSRF exempt for API endpoints

---

### 4. WrestleBot Architecture (Internal)

```
WrestleBot Service
├── main.py (Entry point)
├── config/
│   ├── sources.yaml (All data sources)
│   └── settings.yaml (Service configuration)
├── scrapers/
│   ├── base.py (Base scraper class)
│   ├── wikipedia.py
│   ├── news_rss.py
│   ├── cagematch.py
│   ├── profightdb.py
│   └── ...
├── processors/
│   ├── ai_processor.py (Ollama integration)
│   ├── text_cleaner.py
│   └── entity_linker.py
├── api_client/
│   ├── django_api.py (REST API client)
│   └── auth.py
├── queue/
│   ├── task_queue.py (SQLite-backed task queue)
│   └── retry_handler.py
├── workers/
│   ├── scraper_worker.py (Thread pool for scrapers)
│   ├── processor_worker.py (AI processing)
│   └── publisher_worker.py (Publish to Django)
└── utils/
    ├── logging.py
    ├── metrics.py
    └── health.py
```

---

## Data Flow

### Continuous Operation Loop

```
1. DISCOVER
   ├── Wikipedia: Search for wrestling articles
   ├── RSS Feeds: Check for new articles
   ├── Databases: Scrape wrestler/event data
   └── Store in local queue

2. PROCESS
   ├── Clean and normalize text
   ├── Extract entities (wrestlers, promotions, etc.)
   ├── Verify with Ollama AI (if available)
   ├── Link related entities
   └── Prepare for publishing

3. PUBLISH
   ├── Call Django REST API
   ├── POST /api/wrestlebot/articles/
   ├── POST /api/wrestlebot/wrestlers/
   └── Handle response (success/error)

4. MONITOR
   ├── Log all operations
   ├── Track success/failure rates
   ├── Self-heal circuit breakers
   └── Retry failed operations

5. REPEAT
   └── Go to step 1 (no delay, continuous)
```

---

## Error Handling Strategy

### 1. Circuit Breaker Pattern

```python
class CircuitBreaker:
    """
    Prevent cascading failures from one broken source.
    """

    states = {
        'CLOSED': 'Normal operation',
        'OPEN': 'Too many failures, skip this source',
        'HALF_OPEN': 'Testing if source is back'
    }

    # Configuration
    failure_threshold = 5  # Open circuit after 5 failures
    success_threshold = 2  # Close after 2 successes in HALF_OPEN
    timeout = 300  # Try again after 5 minutes
```

**Application:**
- Wikipedia scraper fails 5 times → Circuit opens for 5 minutes
- Other scrapers continue working
- After 5 minutes, try Wikipedia again
- If success → Circuit closes, resume normal operation

### 2. Retry Queue

```python
class RetryQueue:
    """
    SQLite-backed queue for failed operations.
    """

    retry_delays = [60, 300, 900, 3600]  # 1min, 5min, 15min, 1hr
    max_retries = 4

    def add_failed_task(task, error):
        # Store task in SQLite
        # Schedule retry with exponential backoff
        pass

    def process_retry_queue():
        # Continuously process failed tasks
        # Skip tasks that haven't waited long enough
        pass
```

### 3. Graceful Degradation

**Scenario:** Ollama AI service is down

```python
# Instead of freezing, fallback to simple validation
def verify_wrestler_data(data):
    if ollama_available():
        return ollama_verify(data)  # AI verification
    else:
        return simple_verify(data)  # Regex + basic checks
```

### 4. Source-Specific Error Handling

```python
# If a source gets stuck, move to next
for source in data_sources:
    try:
        with timeout(300):  # 5 minute timeout per source
            data = source.scrape()
            process_data(data)
    except TimeoutError:
        log.warning(f"{source} timed out, moving to next")
        circuit_breaker[source].record_failure()
        continue  # Don't let one source block others
    except Exception as e:
        log.error(f"{source} failed: {e}")
        retry_queue.add(source, data)
        continue
```

---

## Rate Limiting Strategy

### Per-Source Rate Limits

```yaml
sources:
  wikipedia:
    requests_per_minute: 60
    requests_per_hour: 500
    concurrent_requests: 3

  wrestling_inc_rss:
    requests_per_minute: 10
    requests_per_hour: 100
    concurrent_requests: 1

  cagematch:
    requests_per_minute: 5
    requests_per_hour: 50
    concurrent_requests: 1
    user_agent: "WrestleBot/1.0 Educational Research"
```

### Smart Rate Limiting

```python
class SmartRateLimiter:
    """
    Adaptive rate limiter that backs off on errors.
    """

    def __init__(self, base_rate):
        self.rate = base_rate
        self.backoff_multiplier = 1.0

    def on_success(self):
        # Gradually increase rate back to normal
        self.backoff_multiplier = max(1.0,
                                      self.backoff_multiplier - 0.1)

    def on_rate_limit_error(self):
        # Slow down significantly
        self.backoff_multiplier *= 2.0
        self.backoff_multiplier = min(10.0,
                                      self.backoff_multiplier)

    def get_delay(self):
        return (60 / self.rate) * self.backoff_multiplier
```

---

## Wikipedia Full Download Strategy

### Approach 1: Wikipedia Dumps (Recommended)

```python
"""
Download complete Wikipedia dump once, extract wrestling articles.

Advantages:
- No rate limiting
- Complete historical data
- One-time operation

Steps:
1. Download latest Wikipedia dump (50-100 GB compressed)
   - enwiki-latest-pages-articles.xml.bz2

2. Stream parse XML (don't load all into memory)
   - Extract articles containing wrestling keywords
   - Filter by categories

3. Process in batches
   - Extract wrestler/promotion/event data
   - Store in database

4. Delete dump after processing

5. Future updates: Use Wikipedia API for new/changed articles
"""

wikipedia_keywords = [
    "professional wrestling",
    "professional wrestler",
    "WWE", "AEW", "WCW", "ECW", "NJPW",
    "wrestling promotion",
    "wrestling event",
    # ... comprehensive list
]

wikipedia_categories = [
    "Category:Professional wrestlers",
    "Category:Wrestling promotions",
    "Category:Wrestling events",
    # ... full category tree
]
```

### Approach 2: Wikipedia API Bulk Queries

```python
"""
Use Wikipedia API more efficiently.

Instead of:
- One request per article (slow)

Do:
- Bulk category member queries
- Bulk page info requests
- Parallel processing
"""

# Get all articles in a category and subcategories
def get_all_category_members(category, depth=3):
    # Recursively traverse category tree
    # Return all article titles
    pass

# Bulk fetch article content
def bulk_fetch_articles(titles, batch_size=50):
    # Wikipedia API supports up to 50 titles per request
    for batch in chunks(titles, batch_size):
        response = wikipedia_api.query(
            titles='|'.join(batch),
            prop='revisions|categories|pageprops'
        )
        yield response
```

---

## Process Management

### systemd Service (Linux)

```ini
# /etc/systemd/system/wrestlebot.service

[Unit]
Description=WrestleBot Data Collection Service
After=network.target postgresql.service

[Service]
Type=simple
User=wrestlebot
Group=wrestlebot
WorkingDirectory=/opt/wrestlebot
Environment="PATH=/opt/wrestlebot/venv/bin"
ExecStart=/opt/wrestlebot/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Resource limits
LimitNOFILE=65536
MemoryLimit=2G

# Health check
WatchdogSec=60

[Install]
WantedBy=multi-user.target
```

### Supervisor (Alternative)

```ini
# /etc/supervisor/conf.d/wrestlebot.conf

[program:wrestlebot]
command=/opt/wrestlebot/venv/bin/python main.py
directory=/opt/wrestlebot
user=wrestlebot
autostart=true
autorestart=true
startsecs=10
startretries=999
redirect_stderr=true
stdout_logfile=/var/log/wrestlebot/stdout.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
```

### Health Monitoring

```python
# main.py

import signal
import sys
from datetime import datetime

last_heartbeat = datetime.now()

def heartbeat():
    """
    Update heartbeat timestamp.
    systemd WatchdogSec uses this.
    """
    global last_heartbeat
    last_heartbeat = datetime.now()
    # Notify systemd
    notify_systemd("WATCHDOG=1")

def signal_handler(signum, frame):
    """
    Graceful shutdown on SIGTERM/SIGINT.
    """
    logger.info("Received shutdown signal, cleaning up...")
    # Save queue state
    # Close connections
    # Exit cleanly
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Main loop
while True:
    try:
        run_collection_cycle()
        heartbeat()
    except Exception as e:
        logger.error(f"Collection cycle failed: {e}")
        # Don't crash, just log and continue
```

---

## Benefits of This Architecture

### ✅ No More Freezing
- WrestleBot runs outside Celery
- No soft/hard time limits
- Runs indefinitely

### ✅ High Availability
- If one scraper fails, others continue
- Automatic retry of failed operations
- Self-healing circuit breakers

### ✅ Scalability
- Django frontend scales independently
- WrestleBot can run on separate server
- Can run multiple WrestleBot instances (with coordination)

### ✅ Clean Separation of Concerns
- Django: Serve website
- WrestleBot: Collect data
- Clear API boundary

### ✅ Easy Monitoring
- WrestleBot logs to files
- Metrics exportable to Prometheus
- Health endpoints for monitoring

### ✅ Development Friendly
- Can run WrestleBot locally
- Django dev server separate
- Easy to test each component

---

## Migration Path

### Phase 1: Build REST API (Week 1)
1. Create Django REST API endpoints
2. Add token authentication
3. Test with curl/Postman

### Phase 2: Extract WrestleBot (Week 1-2)
1. Create standalone wrestlebot/ directory
2. Copy scraper code from Django
3. Add API client for Django
4. Test locally

### Phase 3: Add Resilience (Week 2)
1. Implement circuit breaker
2. Add retry queue
3. Add error handling
4. Test failure scenarios

### Phase 4: Deploy & Monitor (Week 3)
1. Set up systemd service
2. Deploy to server
3. Monitor logs
4. Tune rate limits

### Phase 5: Scale Up (Ongoing)
1. Add more data sources
2. Increase scraping speed
3. Optimize database writes
4. Add more workers

---

## Configuration Files

### wrestlebot/config/settings.yaml

```yaml
service:
  name: "WrestleBot"
  version: "2.0.0"
  environment: "production"

django:
  api_url: "http://localhost:8000/api/wrestlebot"
  api_token: "${WRESTLEBOT_API_TOKEN}"
  timeout: 30
  retry_attempts: 3

ollama:
  url: "http://localhost:11434"
  model: "llama3.2"
  enabled: true
  fallback_on_failure: true

workers:
  scrapers: 5
  processors: 2
  publishers: 2

logging:
  level: "INFO"
  file: "/var/log/wrestlebot/wrestlebot.log"
  max_size: "100MB"
  backup_count: 5

monitoring:
  metrics_port: 9090
  health_port: 8080
```

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
    rate_limit:
      per_minute: 10
      per_hour: 100

  # ... all other sources
```

---

## Success Metrics

### Performance Goals
- ✅ Zero freezes/timeouts
- ✅ 99.9% uptime for WrestleBot
- ✅ Process 1000+ articles per day
- ✅ Sub-100ms API response time
- ✅ < 5% error rate

### Data Goals
- ✅ Comprehensive Wikipedia coverage (50,000+ wrestlers)
- ✅ Daily news from all major sources
- ✅ Historical data from dumps
- ✅ Real-time RSS feed monitoring

---

**This architecture ensures WrestleBot never freezes and can scale to handle unlimited data sources.**
