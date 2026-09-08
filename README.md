# OWDB — Open Wrestling Database

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.2+-092E20?style=flat&logo=django&logoColor=white)](https://djangoproject.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)](LICENSE)

An open, fan-curated wrestling database and platform — inspired by TMDB and IMDB.

**Website:** [https://wrestlingdb.org](https://wrestlingdb.org)

---

## Features

- **Django 5.2+** web application with PostgreSQL
- **Redis** caching and **Celery** background tasks
- **REST API** with JWT authentication and rate limiting
- **Dark mode** responsive interface
- **Docker Compose** for easy deployment

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 5.2+, Django REST Framework |
| Database | PostgreSQL 15+ |
| Cache | Redis 7+ |
| Task Queue | Celery 5.5+ with Beat scheduler |
| Web Server | Gunicorn + Traefik |
| Containerization | Docker & Docker Compose |

---

## Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/ericrosenberg1/OWDB.git
cd OWDB
cp .env.example .env
docker-compose up --build
# Access at http://localhost:8000
```

### Manual Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## API

```bash
# Get JWT token
curl -X POST https://wrestlingdb.org/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# Use token
curl https://wrestlingdb.org/api/wrestlers/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Rate Limits

| Tier | Requests/Hour |
|------|---------------|
| Free | 100 |
| Authenticated | 1,000 |
| Paid | 10,000 |

---

## Deployment

### Server Requirements

- Ubuntu 22.04+ or similar
- PostgreSQL 15+
- Redis 7+
- Python 3.11+

### Deploy Steps

```bash
ssh root@wrestlingdb.org
cd /home/wrestlingdb
git pull origin main
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python manage.py migrate
./venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart wrestlingdb
```

### Service Management

```bash
# Check status
sudo systemctl status wrestlingdb

# View logs
sudo journalctl -u wrestlingdb -f

# Restart
sudo systemctl restart wrestlingdb
```

---

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- Wrestling data sourced from Wikipedia (factual data only)
- Inspired by [TMDB](https://themoviedb.org) and [IMDB](https://imdb.com)

---

<p align="center">
  <strong>The Open Wrestling Database</strong><br>
  <a href="https://wrestlingdb.org">wrestlingdb.org</a>
</p>
