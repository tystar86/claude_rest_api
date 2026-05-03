# Blogit VPS Rollout Design

## Goal

Deploy the first real application stack behind the new phase-1 Hetzner reverse proxy by making `blog-it.tystar.cz` serve the Blogit frontend and Django backend from this repository.

This design covers both:

- repo-side deployment artifacts
- one manual server rollout path for `/srv/blogit`

## Current State

The host bootstrap work is already in place:

- the Hetzner VPS is reachable over SSH
- Docker and Docker Compose are installed
- the shared `edge` network exists on the VPS
- Caddy is running from `/srv/proxy`
- `tystar.cz`, `www.tystar.cz`, `blog-it.tystar.cz`, and `eat-it.tystar.cz` all resolve to the Hetzner server IP and terminate HTTPS successfully

The current `blog-it.tystar.cz` response is only a Caddy placeholder.

Inside this repo:

- the backend already has a production image path via [Dockerfile.backend](../../../Dockerfile.backend) and [start.sh](../../../start.sh)
- the frontend image at [frontend/Dockerfile.frontend.local](../../../frontend/Dockerfile.frontend.local) is development-oriented and runs the Vite dev server
- the frontend API client in [frontend/src/api/client.js](../../../frontend/src/api/client.js) defaults to `http://localhost:8000/api`, which is correct for local dev but wrong for same-origin production behind Caddy

## Constraints

- Keep the phase-1 VPS architecture from [docs/deployment/vps-phase1-caddy.md](../../deployment/vps-phase1-caddy.md)
- Use one Compose project for Blogit under `/srv/blogit`
- Keep frontend and backend in separate containers
- Keep Postgres private to the Blogit app network
- Keep same-origin `/api` routing so Django session auth, CSRF cookies, and CORS stay simple
- Reuse the existing backend startup flow instead of inventing a second backend runtime path
- Do not introduce CI/CD or a staging environment in this slice

## Approaches Considered

### 1. Recommended: repo artifacts plus one manual VPS rollout

Add the production deploy files to the repo and use them immediately to bring `blog-it.tystar.cz` live on `/srv/blogit`.

Pros:

- proves the real VPS architecture end to end
- keeps phase 1 simple and understandable
- gives quick feedback on Caddy, networking, env vars, and same-origin API behavior

Cons:

- requires a manual rollout procedure
- still leaves automation for later

### 2. Repo artifacts only

Add the deploy files in git but do not touch the server yet.

Pros:

- lower immediate operational risk
- easier to review in isolation

Cons:

- delays verification of the actual host integration
- risks drift between the repo plan and the VPS reality

### 3. Full automation immediately

Add deploy files and a scripted or CI-driven rollout flow now.

Pros:

- fastest path to repeatable deploys later

Cons:

- too much extra machinery for the first app rollout
- makes debugging phase-1 issues harder

## Chosen Design

Use approach 1.

This slice will produce a production-ready frontend container, a VPS-oriented Compose stack for Blogit, a production env template, and the exact Caddy replacement block for `blog-it.tystar.cz`. Then the stack will be rolled out manually on the Hetzner VPS under `/srv/blogit`.

## Target Architecture

### Container layout

The Blogit stack will contain:

- `blogit_frontend`
- `blogit_backend`
- `blogit_db`

Networking:

- `blogit_frontend` joins the app network and the shared `edge` network
- `blogit_backend` joins the app network and the shared `edge` network
- `blogit_db` joins only the app network

Public exposure:

- no Blogit container publishes ports directly to the VPS host
- Caddy reaches `blogit_frontend:80` and `blogit_backend:8000` over `edge`

### Frontend design

Add a production Dockerfile for `frontend/` that:

- installs dependencies
- runs `npm run build`
- serves the built assets from a minimal web server on internal port `80`

The production frontend must default to same-origin API calls. The intended public browser behavior is:

- frontend pages load from `https://blog-it.tystar.cz`
- API calls go to `https://blog-it.tystar.cz/api/...`
- admin stays at `https://blog-it.tystar.cz/admin/...`

To support that, production configuration should stop defaulting to `http://localhost:8000/api` and instead prefer `/api` in production-shaped deployments while preserving the current local-dev override path.

### Backend design

Reuse the existing backend image and startup flow:

- [Dockerfile.backend](../../../Dockerfile.backend)
- [start.sh](../../../start.sh)

This keeps:

- Django migrations in the startup flow
- `collectstatic`
- Gunicorn on port `8000`

Required production env values include:

- `SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS=blog-it.tystar.cz`
- `CSRF_TRUSTED_ORIGINS=https://blog-it.tystar.cz`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- `SECURE_SSL_REDIRECT=True`
- `DB_*` pointing at the Blogit Postgres service

### Database design

Use one Postgres container dedicated to Blogit in phase 1.

Keep it private on the app network, with a named volume for persistence.

## Repo Artifacts To Add

The implementation slice should add:

- a production frontend Dockerfile at `frontend/Dockerfile.frontend.production`
- a Blogit VPS compose file at repo root named `docker-compose.production.yml`
- a tracked production env template at repo root named `.env.example`
- a deployment doc section or companion runbook with exact `/srv/blogit` rollout steps

The compose file should define:

- `blogit_frontend`
- `blogit_backend`
- `blogit_db`
- restart policies
- named volume for Postgres data
- `edge` as an external Docker network

## Caddy Swap

Replace the placeholder `blog-it.tystar.cz` block with:

```caddyfile
blog-it.tystar.cz {
    encode gzip

    handle /api/* {
        reverse_proxy blogit_backend:8000
    }
    handle /admin* {
        reverse_proxy blogit_backend:8000
    }
    handle {
        reverse_proxy blogit_frontend:80
    }
}
```

Important:

- use `handle`, not `handle_path`, so `/api` is not stripped before Django sees it
- Caddy should continue to terminate TLS
- Django should trust proxy HTTPS headers so secure-cookie behavior remains correct

## Manual VPS Rollout Plan

The first real rollout should be:

1. clone this repo directly into `/srv/blogit`
2. copy `.env.example` to `.env.production` inside `/srv/blogit`
3. fill the production secrets and host values in `.env.production`
4. build and start the Blogit Compose stack with `docker compose -f docker-compose.production.yml --env-file .env.production up -d --build`
5. verify `blogit_frontend`, `blogit_backend`, and `blogit_db` are healthy
6. replace the Caddy placeholder block for `blog-it.tystar.cz`
7. reload or restart the proxy stack
8. verify the live site, API, admin, login, and CSRF flow

Expected server paths:

```text
/srv/blogit/
  .env.production
  docker-compose.production.yml
  frontend/Dockerfile.frontend.production
```

## Verification Plan

### Container verification

- `docker compose ps` shows all Blogit services `Up`
- backend logs show Gunicorn started successfully
- frontend serves built assets on internal port `80`
- Postgres is reachable by the backend

### Proxy verification

- `https://blog-it.tystar.cz` returns the frontend, not the placeholder response
- `https://blog-it.tystar.cz/api/auth/csrf/` succeeds
- `https://blog-it.tystar.cz/admin/` routes to Django
- `/api/...` requests keep the `/api` prefix intact

### Functional verification

- browser can load the home page
- frontend API calls use same-origin `/api`
- CSRF cookie bootstrap still works
- login and logout still work
- an authenticated session survives normal page navigation

## Risks And Failure Modes

1. **Frontend API base URL regression**
   If production still points to `http://localhost:8000/api`, the browser will fail or bypass the proxy design.

2. **Caddy path handling regression**
   If `/api` is stripped, Django routes mounted under `/api/` will 404.

3. **Cookie/security regression**
   If Django does not recognize proxy HTTPS correctly, secure cookies or CSRF behavior can fail.

4. **Ops complexity drift**
   If the compose path, env file location, and rollout commands are not made explicit, future deploys become guesswork.

## Out Of Scope

- `tystar.cz` application rollout
- `eat-it.tystar.cz` application rollout
- CI/CD automation
- staging environment setup
- centralized metrics, logs, or alerting
- nameserver migration from Forpsi to Hetzner

## Success Criteria

- `blog-it.tystar.cz` serves the real Blogit frontend over HTTPS
- same-origin `/api` and `/admin` routing works through Caddy
- Django session auth and CSRF still function in production
- the Blogit stack can be rebuilt and restarted from a documented `/srv/blogit` workflow
