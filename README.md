# OWDB — Open Wrestling Database

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.2+-092E20?style=flat&logo=django&logoColor=white)](https://djangoproject.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7+-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-5.5+-37814A?style=flat&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)](LICENSE)

[![GitHub Stars](https://img.shields.io/github/stars/ericrosenberg1/OWDB?style=social)](https://github.com/ericrosenberg1/OWDB/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/ericrosenberg1/OWDB?style=social)](https://github.com/ericrosenberg1/OWDB/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/ericrosenberg1/OWDB)](https://github.com/ericrosenberg1/OWDB/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/ericrosenberg1/OWDB)](https://github.com/ericrosenberg1/OWDB/pulls)
[![Contributors](https://img.shields.io/github/contributors/ericrosenberg1/OWDB)](https://github.com/ericrosenberg1/OWDB/graphs/contributors)
[![Last Commit](https://img.shields.io/github/last-commit/ericrosenberg1/OWDB)](https://github.com/ericrosenberg1/OWDB/commits/main)

[![Snyk Security](https://img.shields.io/badge/Snyk-Protected-4C4A73?style=flat&logo=snyk&logoColor=white)](https://snyk.io)
[![Website](https://img.shields.io/website?url=https%3A%2F%2Fwrestlingdb.org&label=wrestlingdb.org)](https://wrestlingdb.org)

---

An open, fan-curated wrestling database and platform — inspired by TMDB and IMDB.

**Website:** [https://wrestlingdb.org](https://wrestlingdb.org)

---

## Features

- **Django 5.2+** powered web application
- **PostgreSQL** database with full-text search
- **Redis** caching for blazing fast performance
- **Celery** background task processing
- **WrestleBot AI** - Automated data discovery from Wikipedia
- **REST API** with JWT authentication and rate limiting
- **Dark mode** interface with modern responsive design
- **SEO-ready** meta tags and OpenGraph integration
- **Email verification** for new accounts
- **Free and paid API keys** with tiered rate limiting
- **Docker Compose** for easy deployment

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 5.2+, Django REST Framework |
| Database | PostgreSQL 15+ |
| Cache | Redis 7+ |
| Task Queue | Celery 5.5+ with Beat scheduler |
| AI/ML | Ollama (self-hosted LLM) |
| Web Server | Gunicorn |
| Reverse Proxy | Traefik (HTTPS) |
| Containerization | Docker & Docker Compose |

---

## Quick Start

### Local Development (Docker)

```bash
# Clone the repository
git clone https://github.com/ericrosenberg1/OWDB.git
cd OWDB

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up --build

# Access at http://localhost:8000
```

### Manual Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up database
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

---

## API

OWDB provides a comprehensive REST API for accessing wrestling data.

### Authentication

```bash
# Get JWT token
curl -X POST https://wrestlingdb.org/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'

# Use token in requests
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

## WrestleBot

WrestleBot is our AI-powered data discovery system that automatically finds and adds wrestling information from Wikipedia.

- Uses Wikipedia's official API (not scraping)
- Extracts only factual, non-copyrightable data
- Respects rate limits and API terms
- Optional Ollama AI verification
- Runs on a schedule via Celery Beat

### Ollama setup (for Docker users)
- Start the bundled Ollama service: `docker compose up -d ollama`
- Download the model once: `docker compose exec ollama ollama pull llama3.2`
- Ensure `OLLAMA_URL=http://ollama:11434` inside your containers (set automatically in `docker-compose.yml`)

Learn more: [https://wrestlingdb.org/wrestlebot/](https://wrestlingdb.org/wrestlebot/)

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Wrestling data sourced from Wikipedia (factual data only)
- Inspired by [TMDB](https://themoviedb.org) and [IMDB](https://imdb.com)
- Built with love by wrestling fans, for wrestling fans

---

<p align="center">
  <strong>The #1 Open Wrestling Database</strong><br>
  <a href="https://wrestlingdb.org">wrestlingdb.org</a>
</p>
