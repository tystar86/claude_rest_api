# START_HERE

This is the onboarding file for a new developer joining `claude_rest_api`.

## What You Are Looking At

`claude_rest_api` is a full-stack blog platform with:

- A Django 6 + Django REST Framework backend in `blog/`, `accounts/`, and `config/`
- A React 19 + Vite frontend in `frontend/`
- PostgreSQL in local Docker and production
- Session-based auth with Django sessions, CSRF protection, and optional Google OAuth via django-allauth

The quickest way to understand the product is:

1. Open `blog/api_urls.py` to see the public API surface.
2. Open `blog/api_views.py` to see most backend behavior.
3. Open `frontend/src/App.jsx` to see the route map.
4. Open `frontend/src/api/client.js` to see how the frontend talks to the backend.

Operational link:

- Status page: [https://tystar.betteruptime.com/](https://tystar.betteruptime.com/)

## Prerequisites

Choose one local workflow:

- Docker-first: Docker Desktop / Docker Engine + Docker Compose
- Standalone: Python 3.14, Node 22, PostgreSQL 16, and `uv`

Why Python 3.14:

- `.python-version` is pinned to `3.14`
- `pyproject.toml` requires `>=3.14`
- GitHub Actions backend jobs install Python 3.14

Why Node 22:

- Docker uses `node:22-alpine`
- GitHub Actions uses Node 22 for frontend and Robot tests
- The public README still mentions Node 20, but the repo config is more aligned with Node 22

## First-Day Setup

### Option A: Docker

```bash
docker-compose up
```

Services:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Postgres exposed on host port `5433`

What Docker does for you:

- Starts Postgres 16
- Builds the backend image from `Dockerfile.backend`
- Builds the frontend image from `frontend/Dockerfile.frontend`
- Runs backend migrations automatically
- Runs the Vite dev server in the frontend container

### Option B: Standalone

Backend:

```bash
cp .env.local.example .env.local
uv sync --all-groups
uv run python manage.py migrate
uv run python manage.py runserver
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

If you use standalone Postgres, the `.env.local.example` defaults assume:

- DB host `localhost`
- DB port `5432`
- DB name `blog_local`
- DB user/password `postgres`

That differs from Docker, which exposes Postgres on host port `5433`.

## First Sanity Checks

After the app is running:

1. Open `http://localhost:5173/dashboard`
2. Open `http://localhost:8000/api/dashboard/`
3. Open `http://localhost:8000/api/auth/csrf/`

If the frontend loads but writes fail, check:

- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `VITE_API_URL` for production-like frontend runs

## Team Defaults

### Preferred local dataset

Use `seed_large` as the default local dataset when you want a realistic working database:

```bash
uv run python manage.py seed_large
```

Use `loaddata` only when you specifically want a smaller static demo dataset.

### Branch and PR policy

- Target `master` by default
- Never commit directly to `master`
- Always open a PR
- Include the Linear slug in the branch name
- Include the Linear slug in the commit message
- Include the Linear link in the PR description

## How The Repo Is Organized

### Backend

- `config/` holds Django settings, root URLs, ASGI, and WSGI
- `blog/` holds almost all API behavior: models, serializers, throttles, API views, URLs, and management commands
- `accounts/` holds the `Profile` model and the signal that auto-creates a profile for each Django user

Important onboarding note:

- `accounts/views.py` is effectively unused
- Most auth API behavior lives in `blog/api_views.py`, not in `accounts/`

### Frontend

- `frontend/src/App.jsx` declares the route tree
- `frontend/src/api/client.js` centralizes Axios calls and CSRF handling
- `frontend/src/context/AuthContext.jsx` manages current-user bootstrap and logout
- `frontend/src/pages/` contains route-level screens
- `frontend/src/components/` contains shared display building blocks
- `frontend/src/styles/theme.css` defines the app's visual system on top of Bootstrap

### Tests

- `tests/unit/` contains backend pytest coverage
- `frontend/src/**/*.test.jsx` contains frontend Vitest coverage
- `tests/robot/` contains Robot Framework API and UI tests
- `tests/security/` contains standalone security smoke and rate-limit scripts

## Common First Tasks

If you need to:

- Add or change an API endpoint: start in `blog/api_urls.py` and `blog/api_views.py`
- Change serialization: start in `blog/serializers.py`
- Change data shape or relationships: start in `blog/models.py` or `accounts/models.py`
- Change auth/profile behavior: inspect `blog/api_views.py`, `accounts/models.py`, and `accounts/signals.py`
- Change page behavior: start in the matching file under `frontend/src/pages/`
- Change API calls or CSRF behavior: start in `frontend/src/api/client.js`
- Change shared navigation/auth bootstrap: inspect `frontend/src/components/Navbar.jsx` and `frontend/src/context/AuthContext.jsx`

## Environment Files You Should Know

- `.env.local.example`: local standalone baseline
- `.env.testing.example`: fast test defaults
- `.env.production.example`: production template
- `frontend/.env.production`: expected Vercel env shape for `VITE_API_URL`

Runtime behavior:

- Django loads `.env.<DJANGO_ENV>`
- If `DJANGO_ENV` is missing, settings default to `testing` when invoked by pytest and `local` otherwise
- `.env.example` is a generic template, but it is not the file Django auto-loads by default

## Useful Commands

Python/tooling:

```bash
uv sync --all-groups
pytest
uv run pytest tests/unit/
uv run ruff check .
uv run ruff format .
uv run pre-commit run --all-files
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
npm run lint
npm test
npm run test:coverage
```

Robot and security:

```bash
uv run rfbrowser init
uv run robot tests/robot
uv run python tests/security/security_smoke.py --base-url http://localhost:8000
uv run python tests/security/load_burst.py --url http://localhost:8000/api/dashboard/ --requests 250 --concurrency 50
```

## Common Pitfalls

- Test DB mode is different from dev DB mode. Pytest defaults to in-memory SQLite unless `TEST_USE_POSTGRES=true`.
- Standalone local Postgres defaults to host port `5432`, while Docker exposes Postgres on host port `5433`.
- Google OAuth depends on django-allauth under `/accounts/...`, not `/api/auth/...`.
- CSRF is required for session-authenticated write requests. The frontend handles this in `frontend/src/api/client.js`.
- Fixture and large-seed users are useful for data shape and load testing, but they are not a clean source of login-ready accounts.
- A Django `is_staff` or `is_superuser` account is privileged on the backend even if its `Profile.role` still says `user`, so UI role badges can look misleading until the profile is updated.
- Production deploys run `ensure_sites_migrations` before `migrate` because the app has had ordering issues around Django Sites and allauth socialaccount tables.
