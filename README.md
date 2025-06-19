# OWDB — Open Wrestling Database

An open, fan-curated wrestling database API and platform — inspired by TMDB, IMDb, and powered by the community.

Website: [https://wrestlingdb.org](https://wrestlingdb.org)

---

## Features

- Full REST API (Swagger at `/docs`)
- JWT-secured login/authentication
- Editor and Admin roles
- Merge Wizard for duplicate entries
- Rich TinyMCE editor for wrestler bios, events, etc.
- Turnstile bot protection on login/signup
- Dark Mode support
- SEO-ready meta tags and OpenGraph integration
- Open, extensible, free for everyone
- Email verification for new accounts
- Free and paid API keys with rate limiting

---

## Local Development (Docker)

```bash
git clone https://github.com/yourusername/wrestlingdb.git
cd wrestlingdb
cp .env.example .env
docker-compose up --build
```

After signing up, check the console output for a verification link.
