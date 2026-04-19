# Backend Guide

## Stack

- Python 3.14
- Django 6.0
- Django Ninja (`blog/api/`) for HTTP routing, validation, and OpenAPI
- Plain Python serializers in `blog/serializers.py` for read JSON shapes; `blog/services/` for writes (e.g. `PostService`)
- Session-based login and registration via `blog/api/auth/router.py`
- PostgreSQL in real deployments

## App Layout

### `config/`

This is the Django project package:

- `settings.py`: environment loading, installed apps, middleware, DB config, auth, security, Ninja, CORS, email
- `urls.py`: mounts Django admin and API routes
- `wsgi.py` / `asgi.py`: deployment entrypoints

### `blog/`

This is the main application:

- `models.py`: `Tag`, `Post`, `Comment`, `CommentVote`
- `serializers.py`: read serializers used by Ninja routes; `services/` for create/update persistence
- `api_views.py`: shared pagination, dashboard payload, and permission helpers for Ninja
- `api_urls.py`: mounts the Ninja API (`blog.api.api`)
- `api/`: Ninja routers (`auth/`, `data/`), Pydantic schemas, throttling, CSRF helpers
- `management/commands/`: operational commands for seeding and migration repair

### `accounts/`

This app is smaller than the name suggests:

- `models.py`: `Profile` with `user`, `moderator`, and `admin` roles
- `signals.py`: auto-create a `Profile` when a Django `User` is created
- `apps.py`: imports signals at startup

Important note:

- `accounts/views.py` is empty
- API auth/profile HTTP handlers live in `blog/api/auth/router.py`

## Request Flow

Typical API flow:

1. Route enters through `config/urls.py`
2. `/api/...` routes are handed to `blog/api_urls.py` and the Ninja `NinjaAPI` instance
3. Ninja operation functions call helpers in `blog/api_views.py` for pagination, queryset filters, and permission checks
4. JSON payloads are built with `blog/serializers.py` (and Pydantic schemas in `blog/api/**/schemas.py` for response typing)

## Endpoint Groups

### Public read endpoints

- `GET /api/dashboard/`
- `GET /api/activity/` (also `HEAD /api/activity/`)
- `GET /api/comments/`
- `GET /api/posts/`
- `GET /api/posts/<slug>/`
- `GET /api/tags/`
- `GET /api/tags/<slug>/`
- `GET /api/users/`
- `GET /api/users/<username>/`
- `GET /api/users/<username>/comments/`

### Auth and profile endpoints

- `GET /api/auth/csrf/`
- `POST /api/auth/login/`
- `POST /api/auth/register/`
- `POST /api/auth/logout/`
- `GET /api/auth/user/`
- `PATCH /api/auth/profile/`

### Write endpoints

- `POST /api/posts/`
- `PATCH /api/posts/<slug>/`
- `DELETE /api/posts/<slug>/`
- `POST /api/posts/<slug>/comments/`
- `PATCH /api/comments/<id>/`
- `DELETE /api/comments/<id>/`
- `POST /api/comments/<id>/vote/`
- `POST/PATCH/DELETE /api/tags/...`

## Authorization Model

### Authentication

- API auth is session-based (Django sessions + `SessionAuth` in Ninja where applicable)
- Login/logout are handled through `blog/api/auth/router.py`

### Roles

Roles live on `accounts.CustomUser.role`:

- `user`
- `moderator`
- `admin`

### Key authorization helpers

`blog/api_views.py` centralizes reusable checks:

- `can_manage_tags(user)`
- `has_elevated_post_access(user, post)`
- `can_access_comment(user, comment)`

Behavioral summary:

- Authors can manage their own posts and see their own unpublished content
- Moderators and admins can manage tags and moderate more broadly
- Admin/superuser/staff paths get explicit allowances in several view branches

## Data and Serialization

Serializer responsibilities:

- `UserSerializer` and `CurrentUserSerializer` expose profile info and permission hints
- `TagSerializer` and `PostTagSerializer` handle full vs embedded tag representations
- `PostSerializer` is the list/summary shape
- `PostDetailSerializer` adds body and nested comments
- `CommentSerializer` recursively serializes replies and computes vote counts

The serializers do some non-trivial work:

- `CommentSerializer` computes likes, dislikes, and current-user vote state
- `PostDetailSerializer` filters comment visibility based on approval and permissions
- Tag and user serializers can consume annotated counts from views when present

## Settings Behavior Developers Should Know

### Environment selection

`config/settings.py` loads `.env.<DJANGO_ENV>`.

Default behavior:

- `pytest` implies `DJANGO_ENV=testing`
- Everything else defaults to `DJANGO_ENV=local`

### Database selection

- Testing uses in-memory SQLite by default for speed
- Everything else expects PostgreSQL config
- If `TEST_USE_POSTGRES=true`, pytest also uses PostgreSQL

### Static files

- WhiteNoise serves collected static files in deployed environments
- Static files are collected in `start.sh` before Gunicorn launches

### Email

- Local default: console email backend
- Testing: dummy email backend
- Production: optional `EMAIL_BACKEND` / `DEFAULT_FROM_EMAIL` via environment (defaults to console)

## Management Commands

### `ensure_sites_migrations`

Purpose:

- Repairs split migration state for the `django_site` table (`django.contrib.sites`)
- Safe to run repeatedly
- Called automatically in `start.sh`

### `seed_large`

Purpose:

- Generates a large demo dataset for scale/performance testing

## Backend Conventions

- Keep API routes mounted from `blog/api_urls.py`
- Keep Ninja route handlers in `blog/api/`
- Keep shared helpers in `blog/api_views.py`
- Keep serializer changes in `blog/serializers.py`
- Generate migrations with `python manage.py makemigrations`
- Do not hand-edit migration files

## Useful Source Files

- `config/settings.py`
- `config/urls.py`
- `blog/api_urls.py`
- `blog/api/__init__.py`
- `blog/api/auth/router.py`
- `blog/api/data/router.py`
- `blog/api_views.py`
- `blog/serializers.py`
- `blog/models.py`
- `accounts/models.py`
- `accounts/signals.py`
