# Test Server Deployment Plan

This file is intentionally frontend-scoped now.

For the whole-stack VPS/test-server plan, use [docs/deployment/test-server-deployment-plan.md](../docs/deployment/test-server-deployment-plan.md).

## Frontend Recommendation

For a production-like test environment:

- run `npm run build`
- serve the built frontend with Caddy or nginx
- keep API calls same-origin through the reverse proxy
- use `frontend/Dockerfile.frontend.production` rather than the Vite dev server

Why:

- closer to real production
- less memory usage
- fewer moving parts
- better representation of actual user behavior
