# Single-VPS Phase-1 Deployment For Tystar Apps

## Status

Accepted

## Context

The project needs a simple production deployment shape for three public hosts on one VPS:

- `tystar.cz`
- `blog-it.tystar.cz`
- `eat-it.tystar.cz`

Linear issue [TYS-194](https://linear.app/tystar/issue/TYS-194/design-single-vps-deployment-architecture-for-tystarcz-blog-ittystarcz) defines the initial direction: one VPS, shared reverse proxy, and one deploy boundary per app. This repo already runs a Django backend behind Gunicorn via [start.sh](/Users/tystar/Codes/tystar/claude_rest_api/start.sh:1) and exposes Django under `/api/` and `/admin/` in [config/urls.py](/Users/tystar/Codes/tystar/claude_rest_api/config/urls.py:1). The current frontend Dockerfile is dev-oriented, so a production frontend container is a follow-up concern rather than a reason to complicate the overall topology today.

## Decision

We will use a **single VPS** in phase 1 with these boundaries:

- One shared **Caddy** reverse proxy for TLS termination and hostname routing.
- One **Docker Compose project per app** under `/srv`.
- **Same-origin `/api` routing** per hostname for backend-driven apps so Django sessions, CSRF, and cookies stay simple.
- **Separate frontend and backend containers** for `blog-it` and `eat-it`.
- A **static-first `tystar.cz`** deployment unless that site later proves it needs its own backend and database.
- A **dedicated Postgres instance per app** on the VPS for phase 1, with the option to migrate an app to managed Postgres later.

The companion operational note is [docs/deployment/vps-phase1-caddy.md](/Users/tystar/Codes/tystar/claude_rest_api/docs/deployment/vps-phase1-caddy.md:1).

## Consequences

### Positive

- The deploy model stays simple enough to operate manually.
- Each app can be rebuilt and restarted independently.
- Same-origin API routing avoids early CORS and CSRF complexity.
- The architecture matches this repo's current Django and frontend split.

### Negative

- All three hosts share one machine and therefore one failure domain.
- Per-app databases on the VPS still leave backups, restore drills, and disk management as the operator's job.
- A production-ready frontend image is still needed for this repo before the VPS layout is fully implementable.

### Risks / follow-ups

- Add a production frontend container for Blogit instead of using the current Vite dev image.
- Add health checks, restart policies, and backup procedures per app stack.
- Revisit host isolation if one app becomes resource-heavy or security-sensitive.

## Out of scope (optional)

- Multi-node orchestration or autoscaling
- A staging environment
- Full CI/CD pipeline design
- Centralized observability and alerting stack selection
