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
- **REST API** for the core catalog: read-only, browsable with no login, an API key just raises your rate limit
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

Read-only (`GET`) endpoints for the core catalog. Browsing needs no
account. An API key (generate one from
[your account page](https://wrestlingdb.org/account/) once signed in)
doesn't gate access, it just raises your rate limit. Full route list:
`owdb_django/owdbapp/api_urls.py`.

| Resource | List | Detail |
|---|---|---|
| Wrestlers | `GET /api/wrestlers/` | `GET /api/wrestlers/<id>/` |
| Promotions | `GET /api/promotions/` | `GET /api/promotions/<id>/` |
| Events | `GET /api/events/` | `GET /api/events/<id>/` |
| Matches | `GET /api/matches/` | `GET /api/matches/<id>/` |
| Titles | `GET /api/titles/` | `GET /api/titles/<id>/` |
| Venues | `GET /api/venues/` | `GET /api/venues/<id>/` |
| Stables | `GET /api/stables/` | `GET /api/stables/<id>/` |
| Books | `GET /api/books/` | `GET /api/books/<id>/` |
| Video Games | `GET /api/games/` | `GET /api/games/<id>/` |
| Podcasts | `GET /api/podcasts/` | `GET /api/podcasts/<id>/` |
| Specials | `GET /api/specials/` | `GET /api/specials/<id>/` |

List responses are paginated (100 per page) and nest the fields a
consumer actually wants: a match includes wrestler and event *names*,
not bare ids requiring a second request. Write endpoints (`POST`/`PUT`/
`DELETE`) don't exist in v1, this is browse-only.

```bash
# No key needed to browse, at the Free rate limit.
curl https://wrestlingdb.org/api/wrestlers/

# With an API key from your account page, for the higher Authenticated
# (or Paid) rate limit below.
curl https://wrestlingdb.org/api/wrestlers/ \
  -H "X-API-Key: YOUR_KEY"
```

### Rate Limits

| Tier | Requests/Hour |
|------|---------------|
| Free (no key) | 100 |
| Authenticated (has a key) | 1,000 |
| Paid | 10,000 |

---

## Deployment

wrestlingdb.org runs on the NUC at `/home/eric/wrestlingdb` as a Docker Compose
stack behind a Cloudflare Tunnel. Production runs two containers, `web` (Django
under Gunicorn, on SQLite) and `cloudflared`. The `db`, `redis`, and `celery`
services are still defined in `docker-compose.yml` but are pinned to zero
replicas on the NUC by a `docker-compose.nuc.yml` override.

Two things about that directory surprise people:

1. It is **not** a git checkout. There is no `.git`, so there is nothing to
   `git pull`.
2. `docker-compose.nuc.yml` exists only on the NUC, not in this repo. A deploy
   run without it would try to start Postgres, Redis, and Celery, and would bind
   host port 8000, which is already taken on that box.

The canonical update and deploy path is documented in Brian's weekly routine at
`nuc:/home/eric/docker/paperclip/agent-instructions/brian/dependency-updates.md`,
Part I. Follow that. Do not improvise a deploy from this README.

There used to be a `deploy.sh` in this repo. It was removed because every fact
in it was wrong: it targeted `/opt/owdb` (never existed on the NUC), pointed at
a DigitalOcean IP that Eric released and that has since been reassigned to a
third party, and opened with a `git pull` in a directory that is not a
repository.

### Local development

```bash
docker compose up --build
```

### CI

GitHub Actions is disabled on this repo on purpose (billing broke 2026-05-22).
Nothing runs on a pull request and nothing deploys on merge, so test locally
before merging.

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
