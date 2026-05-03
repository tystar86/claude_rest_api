# Test Server Deployment Plan

This note is for a temporary Hetzner-style test VPS that runs one whole app stack at a time for production-like validation.

## Scope

Use this when you want to test the full stack together on one server:

- reverse proxy
- frontend container
- Django backend
- PostgreSQL
- optional Redis / Celery
- optional ASGI/WebSocket services

This is intentionally broader than the frontend-only notes in [frontend/TEST_SERVER_DEPLOYMENT_PLAN.md](../../frontend/TEST_SERVER_DEPLOYMENT_PLAN.md).

## Recommended Shape

Keep one public entrypoint and one internal Docker network:

```text
Internet
  -> Caddy
  -> frontend
  -> backend
  -> postgres
  -> optional redis / celery
```

Guidelines:

- Build the frontend and serve static assets instead of running the Vite dev server.
- Run Django in a container with Gunicorn for standard HTTP traffic.
- Keep Postgres and Redis private on the Docker network.
- Store secrets in a server-side env file, not in Git.
- Put all public traffic through Caddy.

## Repo-Specific Notes

For this repo:

- local full-stack development uses `docker-compose.local.yml`
- the VPS-style production shape uses `docker-compose.production.yml`
- the frontend production image is `frontend/Dockerfile.frontend.production`
- the proxy source of truth lives under [proxy/](../../proxy/)

If you are testing the actual Blogit VPS layout, prefer these docs:

- [Hetzner VPS bootstrap](./hetzner-vps-bootstrap.md)
- [Phase 1 VPS: Caddy + per-app Compose](./vps-phase1-caddy.md)
- [Blogit VPS rollout](./blogit-vps-rollout.md)

## Service Mix

For a production-like single-app test stack, use:

- `proxy`
- `frontend`
- `backend`
- `db`
- optional `redis`
- optional `celery`

WSGI and ASGI apps can share one VPS as separate services. Standard Django HTTP traffic is fine behind Gunicorn WSGI; WebSocket-heavy apps should use ASGI with Uvicorn or Daphne.

## Suggested Server Layout

```text
/srv/test-app/
  docker-compose.yml
  .env.production
  Caddyfile
  app checkout
```

Keep the app root flat where possible instead of nesting an extra repo directory unless you have a specific operational reason.

## Manual Deploy Flow

Start manual first:

```bash
cd /srv/test-app
git pull
docker compose up -d --build
docker compose ps
docker compose logs -f
```

Useful admin commands:

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py shell
docker compose down
docker compose down -v
```

Only use `down -v` when you intentionally want to wipe the database volume.

## CI/CD Follow-Up

Once the manual flow is stable and boring, GitHub Actions can SSH into the server and run the same update/restart sequence. Keep app secrets on the server unless you have a strong reason to inject them through CI.
