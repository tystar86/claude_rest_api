# AGENTS.md — claude_rest_api

A full-stack blog platform with a Django REST Framework backend and React frontend.

---

## Project Structure

```
claude_rest_api/
├── config/          # Django settings, root URLs, ASGI/WSGI
├── blog/            # Posts, comments, tags, votes — core app
├── accounts/        # User profiles and role-based access
├── frontend/        # React 19 + Vite app
├── tests/
│   ├── robot/       # Robot Framework E2E tests (api/ + ui/)
│   └── security/    # Security smoke & load tests
├── docker-compose.yml
├── Dockerfile.backend
├── pyproject.toml
└── .env.*           # .env.local | .env.testing | .env.production
```

---

## Tech Stack

**Backend:** Python 3.14, Django 6.0, Django REST Framework, PostgreSQL 16, django-allauth (Google OAuth), django-cors-headers
**Frontend:** React 19, React Router 7, Vite 8, Bootstrap 5, Axios
**DevOps:** Docker, Docker Compose
**Tooling:** `uv` (Python package manager), Ruff (lint/format), ESLint 9, pre-commit, pytest, Robot Framework

---

## Common Commands

### Docker (recommended — runs full stack)
```bash
docker-compose up                                          # Start all services
docker-compose exec backend python manage.py migrate       # Run migrations
docker-compose exec backend python manage.py createsuperuser
```

Services: Backend → `http://localhost:8000` | Frontend → `http://localhost:5173`

### Backend (standalone)
```bash
uv sync                        # Install Python dependencies
python manage.py migrate       # Apply migrations
python manage.py runserver     # Start dev server
```

### Frontend (standalone)
```bash
cd frontend
npm ci                  # Install dependencies
npm run dev             # Dev server (http://localhost:5173)
npm run build           # Production build
npm run preview         # Preview production build
```

---

## Testing

```bash
# Unit / integration
pytest

# End-to-end (Robot Framework)
robot tests/robot/

# Security & load
python tests/security/security_smoke.py
python tests/security/load_burst.py
```

Environment for tests: `.env.testing` (uses MD5 hasher for speed, DEBUG=False).

---

## Linting & Formatting

```bash
# Python — always run before committing
ruff check .
ruff format .

# JavaScript
cd frontend && npm run lint
```

Pre-commit hooks run automatically: trailing whitespace, Ruff, YAML/JSON/TOML validation, large file detection, debug statement detection. Never bypass with `--no-verify`.

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` (local) / `False` (prod) |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `DB_NAME/USER/PASSWORD/HOST/PORT` | PostgreSQL connection |
| `CORS_ALLOWED_ORIGINS` | Frontend origin (e.g. `http://localhost:5173`) |
| `CSRF_TRUSTED_ORIGINS` | CSRF whitelist |
| `GOOGLE_CLIENT_ID/SECRET` | Google OAuth credentials |
| `DRF_THROTTLE_ANON/USER/ENDPOINT_ACTOR/API_GLOBAL` | Rate limit overrides |

Files: `.env.local` (dev) · `.env.testing` (CI/tests) · `.env.production` (prod template)

---

## API Endpoints (summary)

```
/api/auth/          → login, register, logout, user, profile, csrf
/api/posts/         → list & detail (with comments)
/api/comments/      → CRUD, votes
/api/tags/          → list & detail with posts
/api/users/         → profiles & user comments
/api/dashboard/     → aggregated stats
/admin/             → Django admin
/accounts/          → django-allauth / Google OAuth
```

All endpoints are rate-limited. Default page size: **10**.

---

## Data Models

- **Profile** — extends `User`; roles: `user` / `moderator` / `admin`
- **Post** — slug, body, status (`draft`/`published`), tags, timestamps
- **Comment** — threaded (parent FK), approval workflow
- **CommentVote** — like/dislike on comments
- **Tag** — categorises posts

---

## Coding Conventions

- **Python:** Ruff enforced. Follow existing DRF patterns (`@api_view`, `@permission_classes`). Keep views in `api_views.py`, URLs in `api_urls.py`.
- **JavaScript:** ESLint enforced. Components in `frontend/src/components/`, pages in `frontend/src/pages/`. Use Axios via `frontend/src/api/`.
- **Migrations:** Always generate via `python manage.py makemigrations`; never edit migration files manually.
- **Secrets:** Never commit `.env.*` files or credentials. Use environment variables.
- **Branches:** `main` and `production` are protected (enforced by pre-commit hooks).

---

## Security Notes

- Production requires `SECURE_SSL_REDIRECT=True`, HSTS headers, and secure cookies.
- Review `tests/security/SECURITY_CHECKLIST.md` before deploying.
- CSRF token available at `GET /api/auth/csrf/` — React reads it from cookies.
- Auth is session-based (not JWT), managed by Django sessions.
