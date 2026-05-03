# TheBlog

A full-stack blog platform with a Django + Django Ninja API backend and a React frontend. Features role-based access control, threaded comments with voting, tag management, and session-based email/password auth.

---

## Live Preview

**https://blog-it.tystar.cz/**

## Status Page

[https://tystar.betteruptime.com/](https://tystar.betteruptime.com/)

## Developer Docs

Internal developer documentation now lives in [`docs/developers/README.md`](docs/developers/README.md).

New contributors should start with [`docs/developers/START_HERE.md`](docs/developers/START_HERE.md).

## Tech Stack

### Backend
| | |
|---|---|
| Language | Python 3.14 |
| Framework | Django 6.0 + Django Ninja (`django-ninja`) |
| Database | PostgreSQL 16 |
| Auth | Session-based email/password (Django Ninja `/api/auth/`) |
| Rate limiting | Django Ninja throttling (per-user, per-endpoint, global) |
| Server | Gunicorn |

### Frontend
| | |
|---|---|
| Library | React 19 |
| Router | React Router 7 |
| Build tool | Vite 8 |
| HTTP client | Axios |
| Styling | Custom Neo-Brutalist design system (Space Grotesk + Space Mono) |

### DevOps & Tooling
| | |
|---|---|
| Containerisation | Docker + Docker Compose |
| Python packages | uv |
| Linting | Ruff (Python) · ESLint 9 (JS) |
| Testing | pytest + Robot Framework + Vitest + Testing Library |
| CI hooks | pre-commit (Ruff, YAML/JSON/TOML, secrets detection) |
| Hosting | Hetzner VPS · Caddy · per-app Docker Compose |

---

## Features

- **Posts** — create, edit, delete, and browse published posts; draft workflow
- **Comments** — threaded replies with like/dislike voting; moderation approval
- **Tags** — tag posts and browse posts by tag
- **Users** — public profiles, per-user comment history
- **Dashboard** — aggregated stats (post count, authors, active tags, New posts (7 days), most commented posts)
- **Auth** — email/password registration and login
- **Roles** — `user` · `moderator` · `admin` with enforced permission layers

---

## Running Locally

### Prerequisites
- Docker + Docker Compose, **or** Python 3.14 + Node 20 + PostgreSQL

### Docker (recommended)

```bash
git clone https://github.com/tystar86/claude_rest_api.git
cd claude_rest_api

cp .env.local.example .env.local   # fill in your own non-secret local values
docker-compose up
```

Backend → `http://localhost:8000` | Frontend → `http://localhost:5173`

**Docker Compose** is for **local development** only. It runs Postgres, Django’s `runserver`, and the Vite dev server through `docker-compose.local.yml`. Production uses the Hetzner VPS rollout described in [docs/deployment/vps-phase1-caddy.md](docs/deployment/vps-phase1-caddy.md) and [docs/deployment/blogit-vps-rollout.md](docs/deployment/blogit-vps-rollout.md), with Gunicorn started via `start.sh` and `docker-compose.production.yml`.

### Standalone

**Backend**
```bash
uv sync
cp .env.local.example .env.local   # fill in your own DB credentials and local secrets
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

**Frontend**
```bash
cd frontend
npm ci
npm run dev
```

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` locally, `False` in production |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `DB_NAME / DB_USER / DB_PASSWORD / DB_HOST / DB_PORT` | PostgreSQL connection |
| `CORS_ALLOWED_ORIGINS` | Frontend origin |
| `CSRF_TRUSTED_ORIGINS` | CSRF whitelist |
Files: `.env.local` (dev) · `.env.testing` (tests) · `.env.production.example` (production template) · `.env.vps` (server runtime, untracked)

Never commit real secrets. Keep only placeholder/template values in tracked env files and load live credentials from your local shell or the VPS runtime env file.

---

## API Overview

```
GET  /api/auth/csrf/            CSRF token
POST /api/auth/register/        Create account
POST /api/auth/login/           Email + password login
POST /api/auth/logout/          Logout
GET  /api/auth/user/            Current user
PATCH /api/auth/profile/        Update profile / change password

GET  /api/posts/                Paginated post list
GET  /api/posts/:slug/          Post detail with comments
POST /api/posts/                Create post (auth)
PATCH /api/posts/:slug/         Edit post (author / moderator)
DELETE /api/posts/:slug/        Delete post (author / admin)

GET  /api/comments/             Global comment list
POST /api/posts/:slug/comments/ Add comment (auth)
POST /api/comments/:id/vote/    Like / dislike (auth)

GET  /api/tags/                 Tag list
GET  /api/tags/:slug/           Tag + posts

GET  /api/users/                User list
GET  /api/users/:username/      User profile + posts
GET  /api/users/:username/comments/ User's comments

GET  /api/dashboard/            Aggregated site stats (panels)
GET  /api/activity/             Recent activity for header ticker
```

All list endpoints are paginated (default page size: 50). All write endpoints are rate-limited.

---

## Testing

```bash
# Unit + integration (pytest)
pytest

# Frontend (Vitest)
cd frontend && npm test

# End-to-end (Robot Framework)
robot tests/robot/

# Security smoke + load
python tests/security/security_smoke.py
python tests/security/load_burst.py
```

---

## Project Structure

```
claude_rest_api/
├── config/          # Django settings, root URLs, ASGI/WSGI
├── blog/            # Posts, comments, tags, votes
├── accounts/        # User profiles and roles
├── frontend/        # React 19 + Vite app
│   └── src/
│       ├── api/         # Axios client
│       ├── components/  # Navbar, Pagination, badges
│       ├── context/     # AuthContext
│       └── pages/       # One file per route
├── tests/
│   ├── robot/       # E2E tests (API + UI)
│   └── security/    # Smoke + load tests
├── docker-compose.local.yml
├── docker-compose.production.yml
├── Dockerfile.backend
└── pyproject.toml
```
