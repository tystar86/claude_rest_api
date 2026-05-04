# Blogit VPS Rollout

This runbook turns the shared Hetzner+Caddy phase-1 host into a real deployment target for `blog-it.tystar.cz`.

It assumes:

- [Hetzner VPS bootstrap](./hetzner-vps-bootstrap.md) is complete
- Caddy is already running from `/srv/proxy`
- DNS for `blog-it.tystar.cz` already resolves to the Hetzner VPS
- the shared `edge` Docker network already exists
- the manual [GitHub Actions production release](./github-actions-production-release.md) workflow will be used for application deploys

## Repo Artifacts Used

This rollout uses:

- [docker-compose.production.yml](../../docker-compose.production.yml)
- [.env.example](../../.env.example)
- [frontend/Dockerfile.frontend.production](../../frontend/Dockerfile.frontend.production)

## 1. Create The Production Env File

On the server as `deploy`:

```bash
mkdir -p /srv/blogit
```

From your local checkout:

```bash
scp .env.example deploy@your_server_ip:/srv/blogit/.env.production
```

Then on the server:

```bash
nano /srv/blogit/.env.production
```

Set at least:

- `SECRET_KEY`
- `DB_PASSWORD`
- `POSTGRES_PASSWORD`
- `ALLOWED_HOSTS=blog-it.tystar.cz`
- `CSRF_TRUSTED_ORIGINS=https://blog-it.tystar.cz`
- `CORS_ALLOWED_ORIGINS=https://blog-it.tystar.cz`

Keep `DB_HOST=blogit_db` and `DB_PORT=5432`.

## 2. Run The Production Release Workflow

From GitHub Actions, run the manual [`Production release`](../../.github/workflows/release-production.yml) workflow on the `master` branch.

That workflow will:

- run backend and frontend test gates
- build the backend and frontend images
- push them to private GHCR
- copy [docker-compose.production.yml](../../docker-compose.production.yml) into `/srv/blogit`
- generate `/srv/blogit/.release.env`
- run `docker compose pull && docker compose up -d` on the VPS

## 3. Verify The Blogit Containers

Expected services after the workflow completes:

- `blogit_db`
- `blogit_backend`
- `blogit_frontend`

Useful checks:

```bash
cd /srv/blogit
docker compose -f docker-compose.production.yml --env-file .env.production --env-file .release.env ps
docker compose -f docker-compose.production.yml --env-file .env.production --env-file .release.env logs blogit_backend --tail=100
docker compose -f docker-compose.production.yml --env-file .env.production --env-file .release.env logs blogit_frontend --tail=100
```

## 4. Replace The Caddy Placeholder Block

Edit `/srv/proxy/Caddyfile` and replace the placeholder `blog-it.tystar.cz` block with:

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

- use `handle`, not `handle_path`
- `/api` must reach Django unchanged
- `/admin` also goes to Django
- everything else goes to the frontend container

## 5. Reload The Proxy

On the server:

```bash
cd /srv/proxy
docker compose up -d
docker compose logs --tail=100
```

## 6. Verify The Live Site

From your Mac:

```bash
curl -I https://blog-it.tystar.cz
curl -I https://blog-it.tystar.cz/api/auth/csrf/
curl -I https://blog-it.tystar.cz/admin/
```

What you want:

- the site no longer returns the placeholder plain-text response
- `/api/auth/csrf/` returns a Django response
- `/admin/` is served by Django

## 7. Functional Checks

In the browser, verify:

- the homepage loads
- frontend API requests hit same-origin `/api`
- the CSRF flow works
- login works
- logout works

## Notes

- `/srv/blogit` is the app root on the VPS. There is no repo checkout and no extra nested `claude_rest_api/` directory in the intended layout.
- The frontend production container is built in GitHub Actions and serves the Vite output on internal port `80`.
- The backend reuses the repo’s existing Gunicorn startup path from `start.sh`.
- No Blogit container publishes ports directly to the VPS host; Caddy reaches them over `edge`.
