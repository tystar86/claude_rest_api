# Phase 1 VPS: Caddy + per-app Compose (TYS-194)

This document turns [Linear TYS-194](https://linear.app/tystar/issue/TYS-194/design-single-vps-deployment-architecture-for-tystarcz-blog-ittystarcz) into a concrete server layout. It matches the **one VPS**, **shared reverse proxy**, **one Compose project per app**, and **same-origin `/api`** choices described there.

If you are bootstrapping a fresh Hetzner Ubuntu VPS, follow [hetzner-vps-bootstrap.md](./hetzner-vps-bootstrap.md) first. The tracked proxy source-of-truth lives under [proxy/](/Users/tystar/Codes/tystar/claude_rest_api/proxy/).
For the first real app deployment on this host, follow [blogit-vps-rollout.md](./blogit-vps-rollout.md).

## Goal

Use one VPS as the phase-1 production host for:

- `tystar.cz` as the main public entry point and projects hub
- `blog-it.tystar.cz` as the Blogit app from this repo
- `eat-it.tystar.cz` as a separate app with its own deploy boundary

## Traffic flow

```text
Internet → DNS → VPS public IP → Caddy (TLS) → app Compose network → frontend + backend containers
```

Each app uses its **own** PostgreSQL instance (container on the VPS short-term, or managed Postgres later). Do not share one logical app database across Blogit, EatIt, and the tystar site.

## Phase-1 decisions

- Use **one VPS** and accept shared-host tradeoffs for the initial launch.
- Use **one shared Caddy reverse proxy** for TLS termination and hostname routing.
- Keep **one Compose project per app** so deploys stay isolated.
- Keep **same-origin `/api` routing per hostname** for Django-based apps to simplify CSRF, cookies, and CORS.
- Keep `blog-it` and `eat-it` as **separate frontend + backend + database stacks**.
- Keep `tystar.cz` **static-first** in phase 1 unless it proves it needs its own backend. This is the YAGNI/KISS default.

## App boundaries

| Host | Role | Phase-1 shape |
|------|------|---------------|
| `tystar.cz` | portfolio / presentation site / project directory | frontend container only unless dynamic features are needed |
| `blog-it.tystar.cz` | Blogit app | frontend container + Django backend + Postgres |
| `eat-it.tystar.cz` | EatIt app | frontend container + backend + Postgres |

The `tystar.cz` site should expose a **Projects** view or tab linking out to:

- `https://blog-it.tystar.cz`
- `https://eat-it.tystar.cz`

## Suggested `/srv` layout

```text
/srv/
  proxy/
    docker-compose.yml
    Caddyfile
    .env                    # optional: email for ACME, etc.

  tystar/                   # tystar.cz (marketing / CV / projects hub)
    docker-compose.yml
    .env
    frontend/
      Dockerfile
    ...

  blogit/                   # this repo (blog-it.tystar.cz) — clone path name is your choice
    docker-compose.yml
    .env
    backend/
      Dockerfile
    frontend/
      Dockerfile
    ...

  eatit/
    docker-compose.yml
    .env
    backend/
      Dockerfile
    frontend/
      Dockerfile
    ...
```

If `tystar.cz` later needs forms, admin workflows, or dynamic content management, add a backend and database for that app at that time instead of reserving them up front.

## Shared Docker network

Create a **single external network** once so Caddy can reach each app’s containers by name:

```bash
docker network create edge
```

Each app’s `docker-compose.yml` should:

- Attach its services to `edge` (in addition to an internal default network if you prefer).
- **Not** publish backend `8000` to the host unless you need direct debugging; Caddy talks to `blogit_backend:8000` on `edge`.

The proxy stack joins the same `edge` network and exposes **80** and **443** only.

## Example `Caddyfile` (excerpt)

Replace hostnames if needed. **Option A (recommended):** API under the same hostname as the frontend.

```caddyfile
# Main site
tystar.cz, www.tystar.cz {
    @www host www.tystar.cz
    redir @www https://tystar.cz{uri}

    reverse_proxy tystar_frontend:80
}

# Blogit — claude_rest_api
blog-it.tystar.cz {
    encode gzip

    # Django lives at site paths /api/... and /admin/... — do not strip /api (see config.urls).
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

# EatIt (placeholder service names — adjust to real compose)
eat-it.tystar.cz {
    encode gzip
    handle /api/* {
        reverse_proxy eatit_backend:8000
    }
    handle {
        reverse_proxy eatit_frontend:80
    }
}
```

Notes:

- **`handle_path` would strip `/api`** before proxying; Django expects paths like `/api/dashboard/` (see `config/urls.py`). Use `handle /api/*` with a plain `reverse_proxy` so the path is unchanged.
- If the Django app uses a **URL prefix** via `FORCE_SCRIPT_NAME`, align Caddy with that — otherwise keep `/api/` as the public prefix.
- Serve the **production** SPA from something listening on **port 80 inside** the frontend container (e.g. nginx with `npm run build` assets). The repo’s `frontend/Dockerfile.frontend.local` today targets **Vite dev**; for VPS you want a production image or a multi-stage Dockerfile — track that as a separate implementation task when you build `blogit/docker-compose.production.yml`.
- If `tystar.cz` stays static-only, do not invent a `/api` route there yet. Add one only when that app actually gains a backend.

## Blogit (claude_rest_api) environment checklist

For `blog-it.tystar.cz` with Option A:

| Variable | Example |
|----------|---------|
| `ALLOWED_HOSTS` | `blog-it.tystar.cz` |
| `CSRF_TRUSTED_ORIGINS` | `https://blog-it.tystar.cz` |
| `CORS_ALLOWED_ORIGINS` | `https://blog-it.tystar.cz` (or tighten if everything is same-origin) |
| `SECURE_SSL_REDIRECT` | `True` behind Caddy (set if Django sees HTTPS via `X-Forwarded-Proto`) |
| `DB_*` | Point at the **Blogit-only** Postgres service |

Ensure `config/settings.py` (or your reverse proxy) sets **secure proxy SSL header** semantics so Django treats requests as HTTPS when Caddy terminates TLS.

## Frontend and backend container decision

Keep **frontend and backend in separate containers per app**.

Why this is the phase-1 recommendation:

- It matches how this repo already separates the Vite frontend from the Django backend.
- The frontend can ship as static assets behind nginx or Caddy without carrying Python runtime baggage.
- The backend can keep its current `Dockerfile.backend` and `start.sh` workflow with Gunicorn and migrations.
- Rebuilding one side does not require redeploying the other side unless the app itself changed across both.

## Deploy routine (per app)

Typical sequence for Blogit on the VPS:

1. `docker compose pull` / rebuild images.
2. Run migrations: `docker compose run --rm blogit_backend python manage.py migrate --noinput`.
3. `docker compose up -d` (health checks + restart policies in compose).

## Database decision

- **Phase 1:** one Postgres instance per app on the VPS is acceptable.
- **Later:** move heavier or more critical apps to managed Postgres when backups, failover, or operational isolation matter more than simplicity.
- Do **not** share one logical application database between `tystar`, `blogit`, and `eatit`.

## Out of scope

- Kubernetes, Nomad, or any multi-node scheduler
- blue/green deploy orchestration
- staging environment design
- centralized observability stack
- CI/CD automation beyond noting where it would attach later

## Risk summary (from TYS-194)

One VPS implies shared fate: host compromise, noisy neighbor resource usage, or disk failure affects all three apps. Accept as **phase 1**; split heavier apps to their own VMs or managed services when needed.

Top failure modes to keep in mind:

1. **Ops:** one host outage takes down all three sites at once.
2. **Scaling:** one app can consume CPU, RAM, or disk and degrade neighbors.
3. **Security:** a host-level compromise has wider blast radius than separate VMs.

## Acceptance mapping

| TYS-194 acceptance | Status in this doc |
|--------------------|-------------------|
| Folder structure under `/srv` | Above |
| Proxy routes for the three hosts | Caddyfile excerpt |
| Separate frontend/backend containers | Explicitly chosen above |
| DB on VPS vs managed | Dedicated Postgres **per app** on VPS first; migrate to managed later |

Related GitHub tracking: [claude_rest_api#91](https://github.com/tystar86/claude_rest_api/issues/91).
