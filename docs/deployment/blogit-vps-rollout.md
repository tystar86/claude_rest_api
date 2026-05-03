# Blogit VPS Rollout

This runbook turns the shared Hetzner+Caddy phase-1 host into a real deployment for `blog-it.tystar.cz`.

It assumes:

- [Hetzner VPS bootstrap](./hetzner-vps-bootstrap.md) is complete
- Caddy is already running from `/srv/proxy`
- DNS for `blog-it.tystar.cz` already resolves to the Hetzner VPS
- the shared `edge` Docker network already exists

## Repo Artifacts Used

This rollout uses:

- [docker-compose.production.yml](../../docker-compose.production.yml)
- [.env.example](../../.env.example)
- [frontend/Dockerfile.frontend.production](../../frontend/Dockerfile.frontend.production)

## 1. Clone The Repo On The VPS

On the server as `deploy`:

```bash
cd /srv/blogit
git init
git remote add origin https://github.com/tystar86/claude_rest_api.git
git fetch origin
git checkout -t origin/master
```

If `/srv/blogit` is truly empty and has no existing `.git` directory, a plain clone into that path is also fine. The `git init` flow above is used here because it still works if the bootstrap step already created placeholder folders under `/srv/blogit`.

## 2. Create The Production Env File

```bash
cp .env.example .env.production
nano .env.production
```

Set at least:

- `SECRET_KEY`
- `DB_PASSWORD`
- `POSTGRES_PASSWORD`
- `ALLOWED_HOSTS=blog-it.tystar.cz`
- `CSRF_TRUSTED_ORIGINS=https://blog-it.tystar.cz`
- `CORS_ALLOWED_ORIGINS=https://blog-it.tystar.cz`

Keep `DB_HOST=blogit_db` and `DB_PORT=5432`.

## 3. Build And Start Blogit

```bash
docker compose -f docker-compose.production.yml --env-file .env.production up -d --build
docker compose -f docker-compose.production.yml --env-file .env.production ps
```

If you want logs while the stack settles:

```bash
docker compose -f docker-compose.production.yml --env-file .env.production logs --tail=200
```

## 4. Verify The Blogit Containers

Expected services:

- `blogit_db`
- `blogit_backend`
- `blogit_frontend`

Useful checks:

```bash
docker compose -f docker-compose.production.yml --env-file .env.production ps
docker compose -f docker-compose.production.yml --env-file .env.production logs blogit_backend --tail=100
docker compose -f docker-compose.production.yml --env-file .env.production logs blogit_frontend --tail=100
```

## 5. Replace The Caddy Placeholder Block

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

## 6. Reload The Proxy

On the server:

```bash
cd /srv/proxy
docker compose up -d
docker compose logs --tail=100
```

## 7. Verify The Live Site

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

## 8. Functional Checks

In the browser, verify:

- the homepage loads
- frontend API requests hit same-origin `/api`
- the CSRF flow works
- login works
- logout works

## Notes

- `/srv/blogit` is the app root on the VPS. There is no extra nested `claude_rest_api/` directory in the intended layout.
- The frontend production container builds the Vite app and serves it on internal port `80`.
- The backend reuses the repo’s existing Gunicorn startup path from `start.sh`.
- No Blogit container publishes ports directly to the VPS host; Caddy reaches them over `edge`.
