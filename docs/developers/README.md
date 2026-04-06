# Developer Documentation

This folder is the internal developer guide for `claude_rest_api`.

Recommended reading order:

1. [START_HERE.md](./START_HERE.md) for first-day setup and repo orientation.
2. [backend.md](./backend.md) for Django and DRF structure.
3. [frontend.md](./frontend.md) for React and Vite structure.
4. [database.md](./database.md) for models, migrations, and local DB modes.
5. [security.md](./security.md) for auth, CSRF, CORS, throttling, and release checks.
6. [tooling-testing.md](./tooling-testing.md) for commands, CI, linting, and test workflows.
7. [package-inventory.md](./package-inventory.md) for every declared package, why it exists, and where it is used.

## What This Docs Set Covers

- How to run the app locally with Docker or standalone services
- Where core backend and frontend logic lives
- How the database is modeled and migrated
- How auth and security controls are implemented
- How tests, linting, and CI are wired together
- Which packages appear to be actively used versus only indirectly used or possibly leftover

## Operational Links

- Status page: [https://tystar.betteruptime.com/](https://tystar.betteruptime.com/)

## What Is Intentionally Separated

- Production deploy runbooks are only summarized here. The source-of-truth deploy files are `render.yaml`, `Dockerfile.backend`, `frontend/vercel.json`, and `docker-compose.yml`.
- Feature-by-feature API docs are not broken into a separate reference yet. The best source for endpoint behavior is `blog/api_urls.py` plus `blog/api_views.py`.

## Known Documentation Notes

- The root `README.md` is useful for public/project overview, but these files are more precise for day-to-day development.
- A few repo docs and configs do not fully agree today, especially around branch names and Node version. Those mismatches are called out in [tooling-testing.md](./tooling-testing.md).
