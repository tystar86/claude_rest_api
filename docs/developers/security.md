# Security Guide

## Security Model At A Glance

This project uses:

- Django session authentication
- CSRF protection for authenticated writes
- CORS allowlists
- role-based authorization through `CustomUser.role`
- Django Ninja throttling with scoped limits (anon, user, endpoint, global, login)
- production cookie hardening and HSTS settings

## Authentication

### Primary auth path

- Session-based auth through Django sessions (Ninja `SessionAuth` on protected operations)
- Login, register, logout, current-user, and profile update endpoints are implemented in `blog/api/auth/router.py` (Django Ninja)

## Authorization

The repo uses a combination of:

- ownership checks
- Django staff/superuser checks
- custom user roles

Notable helper functions in `blog/api_views.py`:

- `can_manage_tags`
- `has_elevated_post_access`
- `can_access_comment`

Examples:

- Only authenticated users can create posts or comments
- Tag management is limited to moderator/admin-like users
- Draft posts are only visible to the author or privileged roles
- Unapproved comments are selectively visible based on author/post owner/moderation permissions

## CSRF

CSRF behavior is important because the app uses cookie-based sessions.

Implementation details:

- `GET /api/auth/csrf/` issues the CSRF token
- The frontend reads the `csrftoken` cookie and sends `X-CSRFToken`
- `frontend/src/api/client.js` automatically ensures the token exists before write requests

Config notes:

- `CSRF_COOKIE_HTTPONLY=False` is intentional because the React app needs to read the CSRF cookie
- `CSRF_TRUSTED_ORIGINS` must include the frontend origin for cross-origin local/prod use

## CORS

CORS is handled by `django-cors-headers`.

Key settings:

- `CORS_ALLOWED_ORIGINS`
- `CORS_ALLOW_CREDENTIALS=True`

Local fallback when `DEBUG=True` and the env var is empty:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

## Rate Limiting

The API uses Django Ninja throttling (`blog/api/throttling.py`), wired on routers via `READ_THROTTLES`, `WRITE_THROTTLES`, and `LOGIN_THROTTLES`.

Throttle classes:

- `AnonThrottle`
- `UserThrottle`
- `EndpointActorThrottle`
- `GlobalAPIThrottle`
- `LoginThrottle` (login route stack)

Throttle env vars (legacy names, unchanged for deploys):

- `DRF_THROTTLE_ANON`
- `DRF_THROTTLE_USER`
- `DRF_THROTTLE_ENDPOINT_ACTOR`
- `DRF_THROTTLE_API_GLOBAL`
- `DRF_THROTTLE_LOGIN`

Why this matters:

- The app rate-limits anonymous traffic
- It separately limits authenticated users
- It limits repeated abuse against a single endpoint
- It caps overall API activity per actor

## Secure Settings

Production-relevant settings in `config/settings.py`, `.env.production.example`, and `.env.vps` include:

- `SECURE_SSL_REDIRECT`
- `SECURE_HSTS_SECONDS`
- `SECURE_HSTS_INCLUDE_SUBDOMAINS`
- `SECURE_HSTS_PRELOAD`
- `SESSION_COOKIE_SECURE`
- `SESSION_COOKIE_HTTPONLY`
- `SESSION_COOKIE_SAMESITE`
- `CSRF_COOKIE_SECURE`
- `CSRF_COOKIE_SAMESITE`
- `X_FRAME_OPTIONS`
- `SECURE_CONTENT_TYPE_NOSNIFF`

The settings file also validates invalid SameSite combinations early, especially `SameSite=None` without secure cookies.

## Static and Header Security

Backend:

- Django sets frame and nosniff protections
- WhiteNoise serves static files

Frontend deploy:

- the production frontend is served by nginx in `frontend/Dockerfile.frontend.production`
- Caddy terminates TLS in front of the frontend and backend containers

## Logging

Security-focused logging is configured in `config/settings.py` with:

- `security`
- `django.security`
- `django.request`

This gives the project a dedicated logging channel for suspicious or security-relevant events.

## Security Test Coverage

### Checklist

- `tests/security/SECURITY_CHECKLIST.md`

### Smoke checks

- `tests/security/security_smoke.py`

This script checks:

- security headers
- CORS behavior for unknown origins
- CSRF cookie issuance
- SQL-like path probes
- NoSQL-style payload probes
- XSS reflection behavior
- oversized payload handling
- pagination bounds
- unauthenticated access rejection
- JSON content-type consistency

### Rate-limit burst testing

- `tests/security/load_burst.py`

This is a controlled burst tool for local/staging verification, not an aggressive attack tool.

## Security-Sensitive Operational Notes

- `start.sh` runs `migrate` and `collectstatic` before Gunicorn starts
- Outbound email is optional; default is the Django console backend unless `EMAIL_BACKEND` is set
- Production session and CSRF cookies are expected to be `Secure`
- Cross-origin session auth requires careful coordination between frontend origin, backend origin, and cookie SameSite settings

## Practical Rules For Contributors

- Do not disable CSRF for convenience when using session auth
- Do not broaden CORS to `*` when credentials are enabled
- Keep login throttling stricter than general API throttles
- Review `tests/security/SECURITY_CHECKLIST.md` before release
- When changing auth or cookie behavior, test login, registration, and logout flows end-to-end
