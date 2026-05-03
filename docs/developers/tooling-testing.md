# Tooling And Testing

## Version Expectations

The repo currently points to:

- Python 3.14
- Node 22 in Docker and GitHub Actions
- PostgreSQL 16

Source of truth examples:

- `.python-version` pins Python to `3.14`
- `frontend/Dockerfile.frontend.local` and GitHub Actions pin Node 22

If local tooling and README text disagree, prefer the actual repo configs:

- `Dockerfile.backend`
- `frontend/Dockerfile.frontend.local`
- `.github/workflows/*.yml`
- `pyproject.toml`
- `frontend/package.json`

## Python Tooling

Package management:

- `uv` is the standard package manager
- Python dependency resolution is locked in `uv.lock`

Formatting and linting:

- Ruff handles both lint fixes and formatting
- Pre-commit runs Ruff hooks plus generic file hygiene checks

Main commands:

```bash
uv sync --all-groups
uv run ruff check .
uv run ruff format .
uv run pre-commit run --all-files
```

## Frontend Tooling

Package management:

- npm is used in `frontend/`
- dependencies are locked in `frontend/package-lock.json`

Main commands:

```bash
cd frontend
npm ci
npm run dev
npm run build
npm run preview
npm run lint
npm test
npm run test:coverage
```

## Backend Testing

Pytest config lives in `pyproject.toml`.

Defaults worth knowing:

- `-v`
- `--tb=short`
- `-n auto` via `pytest-xdist`
- `--cov=.`
- `--cov-report=term-missing`

Shared fixtures live in `conftest.py`.

Fast path:

```bash
pytest
```

Focused path:

```bash
uv run pytest tests/unit/
```

## Frontend Testing

Vitest config is embedded in `frontend/vite.config.js`.

Current setup:

- environment `jsdom`
- global test APIs enabled
- setup file `frontend/src/test/setup.js`
- Testing Library assertions from `@testing-library/jest-dom`

The frontend tests currently focus on:

- Dashboard behavior
- Login form behavior
- Register form behavior

## Robot Framework

Robot suites live in:

- `tests/robot/api/`
- `tests/robot/ui/`

Shared resources:

- `tests/robot/resources/common.resource`
- `tests/robot/resources/api.resource`
- `tests/robot/resources/ui.resource`

Setup:

```bash
uv sync --group dev
uv run rfbrowser init
```

Run all:

```bash
uv run robot tests/robot
```

Robot assumptions:

- backend on `http://localhost:8000`
- frontend on `http://localhost:5173`
- moderator credentials can be seeded in CI or pre-created locally

## Security Test Scripts

These are standalone Python scripts, not pytest suites.

Smoke checks:

```bash
uv run python tests/security/security_smoke.py --base-url http://localhost:8000
```

Rate-limit burst:

```bash
uv run python tests/security/load_burst.py --url http://localhost:8000/api/dashboard/ --requests 250 --concurrency 50
```

## Docker Workflows

### Full stack local

```bash
docker-compose up
```

This starts:

- Postgres 16 on host port `5433`
- Django on `8000`
- Vite on `5173`

That full-stack path is **local development only**. Production does not use `docker-compose.local.yml`; the VPS deploy uses `docker-compose.production.yml`, `Dockerfile.backend`, and Gunicorn via `start.sh`.

### Backend container behavior

`Dockerfile.backend` installs dependencies with `uv`.

When you use **Docker Compose**, the `command` in `docker-compose.local.yml` **overrides** the image default and runs Django’s `runserver` (with migrations) instead of `start.sh`. A **production** deploy uses the Dockerfile `CMD` / `start.sh` and Gunicorn through `docker-compose.production.yml`.

`start.sh` then:

1. waits for PostgreSQL
2. runs `migrate`
3. runs `collectstatic`
4. starts Gunicorn

### Debugging the backend with pdb in Docker Compose

The local `backend` service uses Django’s `runserver` with `--nothreading` and `--noreload`, and allocates a TTY so `breakpoint()` / `pdb.set_trace()` can work with `docker attach`. Do **not** rely on a **foreground** `docker compose up` session for typing at the debugger: that terminal is Compose’s log multiplex, not the backend’s stdin.

1. Start the stack in the background (rebuild if you changed the image):

   ```bash
   docker compose -f docker-compose.local.yml up -d --build
   ```

   (`docker-compose -f docker-compose.local.yml up -d --build` is the same with the legacy CLI.)

2. In **another** terminal, attach to the backend container **before** you hit the breakpoint, or as soon as execution stops:

   ```bash
   docker attach claude_rest_api_backend
   ```

3. Reproduce the request in the browser (or client). The `(Pdb)` prompt and your commands should appear in the **attach** terminal.

4. **Detach** from the container **without** stopping it: **Ctrl+P**, then **Ctrl+Q**.

   Avoid **Ctrl+C** while attached unless you intend to send an interrupt to the main process inside the container.

### Frontend container behavior

`frontend/Dockerfile.frontend.local` installs dependencies with `npm ci` and runs Vite.

## CI Workflows

GitHub Actions currently includes four workflows:

- `backend-tests-and-formatting.yml`
- `frontend-tests.yml`
- `robot-tests.yml`
- `security-tests.yml`

What they cover:

- backend pytest and pre-commit
- frontend Vitest and ESLint
- Robot API/UI end-to-end tests
- security smoke and rate-limit checks

## Branch And PR Workflow

Team policy:

- target `master` by default
- never commit directly to `master`
- always open a PR
- include the Linear slug in the branch name
- include the Linear slug in the commit message
- include the Linear link in the PR description

Recommended branch naming pattern:

- `<linear-slug>/<short-topic>`

Recommended commit message pattern:

- `<linear-slug> <short summary>`

## Documentation And Config Mismatches Worth Knowing

These are useful for contributors because they can otherwise waste time:

- Branch-related config is inconsistent with current team policy. Team workflow targets `master`, GitHub Actions trigger on `master` and `testing`, but pre-commit currently protects `main` and `production`.
- The public README says Node 20 is acceptable, but Docker and CI standardize on Node 22.
- The public README mentions pre-commit secret detection, but `.pre-commit-config.yaml` does not currently include a secret-scanning hook.
- `frontend/README.md` is still the default Vite template and does not document this project.
- `frontend/start-dev.sh` runs Vite on port `5174`, but it is not referenced by npm scripts, Docker, or CI.

## Practical Contributor Workflow

Suggested daily loop:

1. `uv sync --all-groups`
2. `cd frontend && npm ci`
3. run the app with Docker or standalone services
4. run focused tests for the area you changed
5. run `uv run pre-commit run --all-files`
6. run frontend lint/tests if you touched the frontend

Recommended minimum before opening a PR:

- backend changes: `pytest`
- frontend changes: `cd frontend && npm run lint && npm test`
- security/auth/routing changes: consider Robot and security smoke scripts too

## django-silk — SQL query profiler (dev only)

How to enable:

1. Uncomment `silk` in `INSTALLED_APPS` in `config/settings.py`
2. Uncomment `silk.middleware.SilkyMiddleware` in `MIDDLEWARE` in `config/settings.py`
3. Uncomment the Silk URL pattern in `config/urls.py`
4. Run `python manage.py migrate` (creates Silk profiling tables)
5. Browse to <http://localhost:8000/silk/>

Usage:

- Silk records every request while enabled.
- `/silk/requests/` — list of HTTP requests with total time and query count
- `/silk/request/{id}/` — drill into one request: each SQL query, duration, `EXPLAIN` plan, and Python traceback
- `/silk/summary/` — aggregated view by endpoint (average time, count)
- `/silk/profiling/` — if `SILKY_PYTHON_PROFILER=True`, shows cProfile output

To profile a specific view with cProfile, decorate it:

```python
from silk.profiling.profiler import silk_profile

@silk_profile(name="post_list")
def post_list(request):
    ...
```

Useful settings (uncomment and adjust in `config/settings.py` as needed):

```python
SILKY_PYTHON_PROFILER = True  # Enable cProfile per-request
SILKY_MAX_RECORDED_REQUESTS = 10_000  # Auto-prune old requests (default: 10k)
SILKY_MAX_RECORDED_REQUESTS_CHECK_PERCENT = 10  # % of requests that trigger prune
SILKY_AUTHENTICATION = True  # Require login to view /silk/
SILKY_AUTHORISATION = True  # Require is_staff to view /silk/
SILKY_INTERCEPT_PERCENT = 100  # % of requests to profile (lower = less overhead)

# ⚠ DEV ONLY — these control how much of each request/response body Silk stores.
# -1 = unlimited and will capture tokens, API keys, and PII in full.
# In production, use conservative limits (bytes) to avoid storing sensitive data:
SILKY_MAX_REQUEST_BODY_SIZE = 1024   # prod recommendation: 1024–5120
SILKY_MAX_RESPONSE_BODY_SIZE = 1024  # prod recommendation: 1024–5120

# Mask sensitive fields in captured data (always configure in any environment):
SILKY_SENSITIVE_KEYS = {"token", "password", "secret", "authorization", "api_key"}
```
