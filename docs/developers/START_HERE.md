# START_HERE

This is the onboarding file for a new developer joining `claude_rest_api`.

## What You Are Looking At

`claude_rest_api` is a full-stack blog platform with:

- A Django 6 backend with Django Ninja HTTP APIs in `blog/api/`, plus `accounts/` and `config/`
- A React 19 + Vite frontend in `frontend/`
- PostgreSQL in local Docker and production
- Session-based auth with Django sessions, CSRF protection, and email/password via `/api/auth/`

The quickest way to understand the product is:

1. Open `blog/api_urls.py` to see how the API is mounted.
2. Open `blog/api/` (Ninja routers and schemas) for HTTP handlers; use `blog/api_views.py` for shared pagination and permission helpers.
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
docker compose -f docker-compose.local.yml up
```

Services:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Postgres exposed on host port `5433`

What Docker does for you:

- Starts Postgres 16
- Builds the backend image from `Dockerfile.backend`
- Builds the frontend image from `frontend/Dockerfile.frontend.local`
- Runs backend migrations automatically
- Runs the Vite dev server in the frontend container

For a fresh Docker Postgres volume and the `seed_large` dataset, see the **Fresh Postgres volume and `seed_large`** subsection in the root `README.md` (Docker section).

**Production vs Compose:** this project does **not** deploy with `docker-compose.local.yml`. The live VPS deployment uses `docker-compose.production.yml`, `Dockerfile.backend`, `frontend/Dockerfile.frontend.production`, and Caddy on the Hetzner host. Use `docker-compose.local.yml` only for local full-stack development (it overrides the backend container to use `runserver`, not Gunicorn).

To debug the backend with `pdb` / `breakpoint()` while using Compose, use a **detached** `up` and **`docker attach`** in a second terminal — see [Debugging the backend with pdb in Docker Compose](./tooling-testing.md#debugging-the-backend-with-pdb-in-docker-compose) in `tooling-testing.md`.

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
- `blog/` holds models, serializers, shared API helpers, URLs, Ninja routers under `blog/api/`, and management commands
- `accounts/` holds `CustomUser` (role and bio live directly on the user record)

Important onboarding note:

- `accounts/views.py` is effectively unused
- Auth HTTP handlers live in `blog/api/auth/router.py`, not in `accounts/`

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

- Add or change an API endpoint: edit `blog/api/` routers (and `blog/api_urls.py` if mount paths change); reuse helpers from `blog/api_views.py` when applicable
- Change serialization: start in `blog/serializers.py`
- Change data shape or relationships: start in `blog/models.py` or `accounts/models.py`
- Change auth/profile behavior: inspect `blog/api/auth/router.py` and `CustomUser` in `accounts/models.py` (role, bio, and related fields)
- Change page behavior: start in the matching file under `frontend/src/pages/`
- Change API calls or CSRF behavior: start in `frontend/src/api/client.js`
- Change shared navigation/auth bootstrap: inspect `frontend/src/components/Navbar.jsx` and `frontend/src/context/AuthContext.jsx`

## Environment Files You Should Know

- `.env.local.example`: local standalone baseline
- `.env.testing.example`: fast test defaults
- `.env.example`: tracked production template
- `.env.production`: production runtime env file copied from `.env.example` and kept untracked

Runtime behavior:

- Django loads `.env.<DJANGO_ENV>`
- If `DJANGO_ENV` is missing, settings default to `testing` when invoked by pytest and `local` otherwise
- `.env.example` is the tracked template for production-style settings, but Django still does not auto-load it directly

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
- CSRF is required for session-authenticated write requests. The frontend handles this in `frontend/src/api/client.js`.
- Fixture and large-seed users are useful for data shape and load testing, but they are not a clean source of login-ready accounts.
- A Django `is_staff` or `is_superuser` account is privileged on the backend even if its `CustomUser.role` still says `user`, so UI role badges can look misleading until the user role is updated.
