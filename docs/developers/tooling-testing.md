# Tooling And Testing

## Version Expectations

The repo currently points to:

- Python 3.14
- Node 22 in Docker and GitHub Actions
- PostgreSQL 16

Source of truth examples:

- `.python-version` pins Python to `3.14`
- `frontend/Dockerfile.frontend` and GitHub Actions pin Node 22

If local tooling and README text disagree, prefer the actual repo configs:

- `Dockerfile.backend`
- `frontend/Dockerfile.frontend`
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

### Backend container behavior

`Dockerfile.backend` installs dependencies with `uv`.

`start.sh` then:

1. waits for PostgreSQL
2. runs `ensure_sites_migrations`
3. runs `migrate`
4. runs `collectstatic`
5. starts Gunicorn

### Frontend container behavior

`frontend/Dockerfile.frontend` installs dependencies with `npm ci` and runs Vite.

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
