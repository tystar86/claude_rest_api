# Database Guide

## Primary Database

The intended primary database is PostgreSQL 16.

Where that shows up:

- `docker-compose.yml` uses `postgres:16-alpine`
- `render.yaml` is configured for a production PostgreSQL service
- `start.sh` uses `psycopg` to wait for database readiness
- Django settings build a PostgreSQL connection unless tests intentionally switch to SQLite

## Local and Test Modes

### Local dev

Standalone local settings expect PostgreSQL from `.env.local`.

Docker local uses:

- container name `claude_rest_api_db`
- host port `5433`
- DB name `claude_rest_api`
- DB user/password `claude_rest_api`

### Tests

Pytest behavior is important:

- Default test mode is in-memory SQLite for speed
- Set `TEST_USE_POSTGRES=true` to run tests against PostgreSQL
- CI does force PostgreSQL for backend and Robot workflows

This means:

- Some migration or PostgreSQL-specific behavior may not appear in the default fast local test path
- `ensure_sites_migrations` tests are explicitly marked to require PostgreSQL behavior

## Models and Relationships

### `accounts.Profile`

- One-to-one with Django `User`
- Adds `role` and `bio`
- Roles are `user`, `moderator`, and `admin`

### `blog.Tag`

- `name`
- `slug`

Used to categorize posts through a many-to-many relationship.

### `blog.Post`

- belongs to a `User` author
- has `title`, `slug`, `body`, `excerpt`
- has `status` of `draft` or `published`
- has many-to-many tags
- tracks `created_at`, `updated_at`, `published_at`

### `blog.Comment`

- belongs to a `Post`
- belongs to a `User` author
- can reference a parent comment for threaded replies
- has moderation state via `is_approved`

### `blog.CommentVote`

- belongs to a comment
- belongs to a user
- vote type is `like` or `dislike`
- unique per `(comment, user)`

## Relationship Summary

- User -> Profile: one-to-one
- User -> Post: one-to-many
- User -> Comment: one-to-many
- User -> CommentVote: one-to-many
- Post -> Tag: many-to-many
- Post -> Comment: one-to-many
- Comment -> Comment: parent/replies self-reference
- Comment -> CommentVote: one-to-many

## Indexes and Performance Notes

The models include explicit indexes beyond default primary keys.

### Post indexes

- `status, published_at`
- `author`
- `status, -created_at`

These support:

- published-list filtering
- author lookups
- reverse-chronological feeds

### Comment indexes

- `-created_at`
- `post, created_at`

These support:

- global comment feeds
- per-post comment ordering

### CommentVote indexes

- `comment, vote`

This supports vote aggregation paths.

## Migrations

Current apps with repo-owned migrations:

- `accounts/migrations/`
- `blog/migrations/`

Important repo rule:

- Generate migrations with Django commands
- Do not hand-edit migration files

There is also a repo-specific migration repair mechanism:

- `accounts/migrations/0003_enforce_sites_dependency.py`
- `blog/management/commands/ensure_sites_migrations.py`

Those exist because `django.contrib.sites` has occasionally shown split migration state in deployed environments.

## Fixtures and Seed Data

Preferred local dataset:

- `python manage.py seed_large`

### Fixture file

- `blog/fixtures/initial_data.json`

This looks like a starter/demo fixture, but there is no main documented workflow in the repo for when contributors should load it.

Important limitation:

- the fixture is useful for content shape and browsing
- it should not be assumed to provide login-ready demo users

### Large seed command

- `python manage.py seed_large`

Use this when you need:

- performance-like datasets
- pagination volume
- broader dashboard data
- lots of users, posts, tags, comments, and votes

Important limitation:

- the generated users are not a clean source of ready-to-use human login accounts for onboarding

## Database Environment Variables

Core DB variables:

- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `DB_CONN_MAX_AGE`

Test control variable:

- `TEST_USE_POSTGRES`

Production-related DB behavior:

- `DB_CONN_MAX_AGE` controls persistent connections
- `CONN_HEALTH_CHECKS` is enabled by default when persistent connections are used

## Common Database Workflows

Create and apply migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

Load a fixture manually if you choose to use it:

```bash
python manage.py loaddata blog/fixtures/initial_data.json
```

Generate a large demo dataset:

```bash
python manage.py seed_large
```

Repair sites migration state before or during deploy troubleshooting:

```bash
python manage.py ensure_sites_migrations
python manage.py migrate
```

## What New Developers Should Keep In Mind

- SQLite test behavior is convenient but not identical to PostgreSQL
- The deploy path assumes PostgreSQL and includes extra migration safety logic
- Data visibility is shaped by both post publication status and comment approval state
- If you are debugging auth-related data, inspect Django `auth_user` and `accounts_profile`, not only content tables
- If you need a privileged human test account, `createsuperuser` plus an explicit `Profile.role` update is more reliable than relying on fixtures or bulk seed data
