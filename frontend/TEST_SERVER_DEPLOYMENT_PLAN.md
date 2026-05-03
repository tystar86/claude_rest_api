# Test Server Deployment Plan

This plan describes a production-like deployment setup for a single Hetzner test VPS that runs one full app stack at a time:

- Django backend
- React frontend
- PostgreSQL
- Redis
- Celery worker
- reverse proxy

The goal is to keep the setup simple enough for learning and testing while still resembling a real deployment.

## Goal

Use one VPS as a temporary full-stack lab:

1. Deploy one app stack.
2. Test backend, frontend, database, background jobs, and optional WebSockets together.
3. Replace that stack later with another app when needed.

This is the best fit for a smaller server such as `CX23`.

## Recommended Architecture

One public entrypoint, one internal Docker network.

```text
Internet
  |
  v
Reverse proxy (Caddy or Nginx)
  |-- /            -> React frontend
  |-- /api/        -> Django backend
  |-- /admin/      -> Django backend
  |-- /ws/         -> ASGI Django app when WebSockets are needed

Internal services:
  - postgres
  - redis
  - celery worker
```

## Production-Like Principles

To stay close to production, prefer this shape:

- Build the frontend and serve static assets, instead of running the Vite dev server.
- Run the Django app in a container, not with a bind-mounted source tree.
- Keep Postgres and Redis private on the Docker network.
- Put all public traffic through one reverse proxy.
- Store secrets in a server-side `.env` file, not in Git.
- Use HTTPS once the domain is attached.

## WSGI And ASGI On The Same Server

Yes, this is okay.

A WSGI Django app and an ASGI Django app can live next to each other on the same VPS as long as they run as separate services or containers.

Example:

- `blog-app-backend` on port `8000` using Gunicorn WSGI
- `chat-app-backend` on port `8001` using Uvicorn or Daphne ASGI
- reverse proxy routes traffic by hostname or path

Typical split:

- `api1.example.com` -> WSGI app
- `api2.example.com` -> ASGI app

or

- `example.com/app1/` -> WSGI app
- `example.com/app2/` -> ASGI app

Important note:

- A WSGI app is fine for standard HTTP requests.
- A WebSocket app should be deployed with ASGI, not WSGI.

For this repo specifically, the current backend startup script uses WSGI Gunicorn, which is fine for the current HTTP app. A future Channels-based app should use an ASGI server.

## Services On The Test Server

For a production-like single-app stack, use these services:

- `proxy`
- `frontend`
- `backend`
- `db`
- `redis`
- `celery`

Optional later:

- `celery-beat`
- `flower`

## Suggested Directory Layout On The VPS

```text
/srv/test-app/
  docker-compose.test.yml
  .env
  Caddyfile or nginx.conf
  backend/ or repo checkout
```

If deploying directly from this repository:

```text
/srv/test-app/claude_rest_api
```

## Environment Variables

Keep secrets on the server in `.env`.

Example values:

```env
SECRET_KEY=replace-me
DEBUG=False
ALLOWED_HOSTS=your-domain.example
DB_NAME=app_db
DB_USER=app_user
DB_PASSWORD=replace-me
DB_HOST=db
DB_PORT=5432
REDIS_URL=redis://redis:6379/0
CORS_ALLOWED_ORIGINS=https://your-domain.example
CSRF_TRUSTED_ORIGINS=https://your-domain.example
```

For test-only deployments without a domain yet:

- use the server IP temporarily
- update `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS` accordingly

## Recommended Deploy Flow

Start manual first.

Manual deployment is good because it teaches the moving parts:

- Docker images
- env vars
- migrations
- restart flow
- logs

Once this is stable and boring, add GitHub Actions.

## Manual Deployment Workflow

Initial server bootstrap:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
```

Install Docker using the official Docker instructions for the target OS.

Application lifecycle:

```bash
cd /srv/test-app/claude_rest_api
git pull
docker compose -f docker-compose.test.yml up -d --build
docker compose -f docker-compose.test.yml ps
docker compose -f docker-compose.test.yml logs -f
```

Useful admin commands:

```bash
docker compose -f docker-compose.test.yml exec backend python manage.py migrate
docker compose -f docker-compose.test.yml exec backend python manage.py createsuperuser
docker compose -f docker-compose.test.yml exec backend python manage.py shell
docker compose -f docker-compose.test.yml down
docker compose -f docker-compose.test.yml down -v
```

Notes:

- `down` stops the stack.
- `down -v` also deletes the database volume and should only be used when a full reset is desired.

## CI/CD Option With GitHub Actions

After manual deploy works, GitHub Actions can update the server automatically.

High-level flow:

1. Push code to GitHub.
2. GitHub Actions runs tests.
3. If tests pass, the workflow connects to the VPS over SSH.
4. The VPS updates the repo and restarts the stack.

Server-side deploy commands:

```bash
cd /srv/test-app/claude_rest_api
git pull
docker compose -f docker-compose.test.yml up -d --build
```

Recommended GitHub secrets:

- `VPS_HOST`
- `VPS_USER`
- `VPS_SSH_KEY`
- optional `VPS_PORT`

Keep app secrets on the server, not in GitHub Actions, unless there is a strong reason not to.

## Frontend Recommendation

For a production-like test environment:

- run `npm run build`
- serve the built frontend with Caddy or Nginx

Avoid using the Vite dev server on the VPS except for temporary debugging.

Why:

- closer to real production
- less memory usage
- fewer moving parts
- better representation of actual user behavior

## Backend Recommendation

For a standard Django HTTP app:

- Gunicorn WSGI is fine

For an app using Channels or WebSockets:

- use ASGI with Uvicorn or Daphne
- keep Redis available as the channel layer backend

## Database And Redis Recommendation

For a single test app on one VPS:

- Postgres and Redis can safely live on the same server
- they should not be directly exposed to the internet
- Docker internal networking is enough

This is normal for a staging or test environment.

## Reverse Proxy Recommendation

Prefer Caddy for the first version because it is simpler to configure.

Suggested behavior:

- serve frontend static files
- reverse proxy `/api/` and `/admin/` to Django
- reverse proxy `/ws/` to the ASGI app when needed
- terminate HTTPS automatically once the domain is attached

## Out Of Scope

- Kubernetes
- multi-server deployments
- separate managed Postgres or Redis
- blue/green deployments
- autoscaling
- multiple apps running permanently on a `CX23`

## Practical Recommendation

Start with:

- one app stack at a time
- one domain or temporary IP-based deploy
- manual Docker Compose deploy
- built React frontend
- Django backend
- Postgres and Redis on the same VPS

Then add:

- GitHub Actions deploy
- HTTPS and domain routing
- ASGI app deployment for WebSocket projects

## Next Files To Create

When implementing this plan, create:

- `docker-compose.test.yml`
- frontend production Dockerfile or adjusted frontend container setup
- `Caddyfile` or `nginx.conf`
- optional GitHub Actions workflow such as `.github/workflows/deploy-test.yml`
