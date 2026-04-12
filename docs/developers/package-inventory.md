# Package Inventory

This file lists the packages declared directly by the repo, why they appear to be here, and where they are used.

Observed usage levels:

- `Active`: direct imports, config, or scripts clearly use it
- `Indirect`: no obvious imports, but the package likely supports another declared feature
- `Unclear`: no direct usage was found during the scan

## Python Runtime Packages

| Package | Why It Is Here | Where It Is Used | Status |
| --- | --- | --- | --- |
| `dj-database-url` | Builds Django DB settings from environment variables | `config/settings.py` | Active |
| `django` | Core backend framework | `manage.py`, `config/`, `blog/`, `accounts/`, tests | Active |
| `django-cors-headers` | CORS middleware and settings | `config/settings.py` | Active |
| `django-ninja` | HTTP API routing, OpenAPI, request validation | `blog/api/`, `pyproject.toml` | Active |
| `gunicorn` | Production WSGI server | `start.sh` | Active |
| `psycopg` | PostgreSQL driver and DB readiness checks | `start.sh`, Django DB backend usage from `config/settings.py` | Active |
| `python-dotenv` | Loads `.env.<DJANGO_ENV>` files in development and tests | `config/settings.py` | Active |
| `requests` | Used by standalone security smoke and burst scripts | `tests/security/security_smoke.py`, `tests/security/load_burst.py` | Active |
| `whitenoise` | Serves Django static files and provides compressed manifest storage | `config/settings.py` | Active |

## Python Dev And Test Packages

| Package | Why It Is Here | Where It Is Used | Status |
| --- | --- | --- | --- |
| `pre-commit` | Runs repo hygiene hooks before commits | `.pre-commit-config.yaml`, CI workflow `backend-tests-and-formatting.yml` | Active |
| `pytest` | Main backend test runner | `pyproject.toml`, `tests/unit/` | Active |
| `pytest-cov` | Coverage reporting for pytest | `pyproject.toml` addopts | Active |
| `pytest-django` | Django-aware pytest integration | `pyproject.toml`, `conftest.py`, `tests/unit/` | Active |
| `pytest-xdist` | Parallel pytest execution via `-n auto` | `pyproject.toml` addopts | Active |
| `robotframework` | End-to-end test runner | `tests/robot/README.md`, `tests/robot/**/*.robot` | Active |
| `robotframework-browser` | Browser automation for Robot UI tests | `tests/robot/resources/ui.resource`, Robot setup docs | Active |
| `robotframework-requests` | HTTP client support for Robot API tests | `tests/robot/resources/api.resource` | Active |
| `ruff` | Python linting and formatting | `.pre-commit-config.yaml`, contributor commands | Active |

## Frontend Runtime Packages

| Package | Why It Is Here | Where It Is Used | Status |
| --- | --- | --- | --- |
| `axios` | HTTP client for backend API calls and CSRF-aware writes | `frontend/src/api/client.js` | Active |
| `bootstrap` | Base CSS/layout/component system | `frontend/src/main.jsx`, class usage across `frontend/src/pages/` and `frontend/src/components/` | Active |
| `bootstrap-icons` | Icon font for UI icons | `frontend/src/main.jsx`, icon classes in components/pages | Active |
| `react` | UI framework | `frontend/src/` | Active |
| `react-dom` | DOM renderer | `frontend/src/main.jsx` | Active |
| `react-router-dom` | Client-side routing and navigation | `frontend/src/App.jsx`, `frontend/src/components/Navbar.jsx`, `frontend/src/pages/` | Active |

## Frontend Dev And Test Packages

| Package | Why It Is Here | Where It Is Used | Status |
| --- | --- | --- | --- |
| `@eslint/js` | Base ESLint rule set for flat config | `frontend/eslint.config.js` | Active |
| `@testing-library/jest-dom` | Better DOM assertions for tests | `frontend/src/test/setup.js` | Active |
| `@testing-library/react` | React component rendering utilities for tests | `frontend/src/pages/*.test.jsx` | Active |
| `@testing-library/user-event` | Simulated user interactions in tests | `frontend/src/pages/Login.test.jsx`, `frontend/src/pages/Register.test.jsx` | Active |
| `@types/react` | Editor/type support package even though the app is plain JS | Declared in `frontend/package.json`; no `.ts` or `.tsx` sources found | Indirect |
| `@types/react-dom` | Editor/type support package even though the app is plain JS | Declared in `frontend/package.json`; no `.ts` or `.tsx` sources found | Indirect |
| `@vitejs/plugin-react` | Vite React integration | `frontend/vite.config.js` | Active |
| `@vitest/coverage-v8` | Coverage provider for `npm run test:coverage` | `frontend/package.json` script | Active |
| `eslint` | Frontend lint runner | `frontend/package.json`, `frontend/eslint.config.js` | Active |
| `eslint-plugin-react-hooks` | React Hooks lint rules | `frontend/eslint.config.js` | Active |
| `eslint-plugin-react-refresh` | React Refresh-compatible export rules | `frontend/eslint.config.js` | Active |
| `globals` | Browser and test globals for ESLint flat config | `frontend/eslint.config.js` | Active |
| `jsdom` | Browser-like DOM environment for Vitest | `frontend/vite.config.js` | Active |
| `vite` | Frontend dev server and build tool | `frontend/package.json`, `frontend/vite.config.js`, Docker and CI commands | Active |
| `vitest` | Frontend test runner | `frontend/package.json`, `frontend/vite.config.js`, `frontend/src/**/*.test.jsx` | Active |

## Packages Worth Reviewing

Removed from direct dependencies during cleanup:

- `pillow`
- `pyjwt`
- `cryptography`

These frontend packages may still be worth reviewing:

- `@types/react`
- `@types/react-dom`

If you want to trim dependencies safely, verify with:

1. local runtime boot
2. backend pytest
3. frontend Vitest
4. Robot tests
5. production build/deploy path
