# DRF To Django Ninja Architecture Design

## Goal

Create the migration foundation for the full DRF-to-Django-Ninja rewrite without breaking the current public API contract.

This design covers `TYS-172` directly and defines the first implementation slice for `TYS-173`.

## Current State

The public API currently has one stable mount point and one dominant implementation layer:

- `/api/` is mounted in [config/urls.py](/Users/tystar/Codes/tystar/claude_rest_api/config/urls.py:1)
- the concrete route table lives in [blog/api_urls.py](/Users/tystar/Codes/tystar/claude_rest_api/blog/api_urls.py:1)
- almost all API behavior lives in [blog/api_views.py](/Users/tystar/Codes/tystar/claude_rest_api/blog/api_views.py:1)
- most response shapes are defined in [blog/serializers.py](/Users/tystar/Codes/tystar/claude_rest_api/blog/serializers.py:1)
- throttling lives in [blog/throttles.py](/Users/tystar/Codes/tystar/claude_rest_api/blog/throttles.py:1)
- the frontend is tightly coupled to current auth, CSRF, error, and pagination behavior through [frontend/src/api/client.js](/Users/tystar/Codes/tystar/claude_rest_api/frontend/src/api/client.js:1) and [frontend/src/context/AuthContext.jsx](/Users/tystar/Codes/tystar/claude_rest_api/frontend/src/context/AuthContext.jsx:1)

The repo already depends on `django-ninja`, but there was no active Ninja API package or router usage before this migration start.

## Constraints

- Keep the current `/api/...` public paths stable during the first migration phase
- Preserve session-cookie auth; do not switch to JWT
- Preserve CSRF bootstrap behavior:
  - `GET /api/auth/csrf/` returns `{ "csrfToken": ... }`
  - the response also sets the `csrftoken` cookie
  - mutating requests continue to use `X-CSRFToken`
- Preserve the current custom pagination envelope:
  - `{ count, total_pages, page, results }`
- Preserve current auth payload shapes, especially the raw current-user object used by the frontend
- Preserve current error semantics where the UI or tests depend on them:
  - `detail` envelopes for auth/not-found/generic cases
  - field-keyed dictionaries for profile validation failures
- Avoid dual-maintenance at the public contract layer longer than necessary, but allow an internal preview seam while the new foundation is proven

## Contract Inventory

### Auth and bootstrap contracts

The most contract-sensitive routes for the first slice are:

- `GET /api/auth/csrf/`
- `POST /api/auth/login/`
- `POST /api/auth/register/`
- `POST /api/auth/resend-verification/`
- `POST /api/auth/logout/`
- `GET /api/auth/user/`
- `PATCH /api/auth/profile/`

The must-preserve auth behavior for the first migration phase is:

- exact `/api/auth/...` path stability
- raw current-user payload shape from `CurrentUserSerializer`
- generic `"Invalid credentials."` login failures
- generic `"Registration failed."` duplicate-registration failures
- mandatory-email-verification branching for both registration and login
- `401` vs `403` status splits where tests already pin them
- session continuity across CSRF bootstrap, login, and authenticated requests
- login and resend-verification throttling behavior

### Collection and detail contracts

The highest-coupling non-auth contracts are:

- paginated collections using `{ count, total_pages, page, results }`
- mixed detail payloads for tags and users:
  - `{ tag, count, total_pages, page, results }`
  - `{ user, count, total_pages, page, results }`
- embedded post-detail comment trees
- dashboard top-level keys:
  - `stats`
  - `latest_posts`
  - `most_commented_posts`
  - `most_used_tags`
  - `top_authors`

## Approaches Considered

### 1. Recommended: compatibility-first Ninja foundation

Create a new `blog/api/` Ninja package, keep the public DRF contract stable, and migrate by vertical slices.

Pros:

- lowest frontend and test risk
- lets us validate CSRF, session auth, and throttling before broad endpoint moves
- keeps migration intent explicit instead of burying it inside the legacy module

Cons:

- temporarily keeps both DRF and Ninja code in the repo
- requires a compatibility layer for error and pagination behavior

### 2. Contract-cleanup-first rewrite

Use the framework migration to also normalize routes, pagination, and errors immediately.

Pros:

- cleaner long-term API design
- fewer legacy patterns carried forward

Cons:

- too much client and test churn at once
- makes regressions harder to isolate
- turns architecture work into a multi-surface rewrite

### 3. Full cutover behind one new Ninja root immediately

Replace the existing `/api/` implementation in one move and update all clients and tests together.

Pros:

- fastest path to a pure Ninja runtime

Cons:

- highest regression risk
- hardest rollback path
- not a good fit for the repo’s current frontend and Robot coupling

## Chosen Design

Use a compatibility-first Ninja migration.

The new code lives in `blog/api/`, but the current public API surface remains the source of truth while the migration is being validated. The first implementation slice is a preview auth surface under `/api/_ninja/auth/` so we can prove the new CSRF and session mechanics without destabilizing the public DRF endpoints yet.

Once the preview slice proves parity, the public auth routes can be cut over one by one, then the remaining domains can migrate in the order defined below.

## Target Architecture

The target structure is:

```text
blog/
  api_urls.py
  api_views.py
  api/
    __init__.py
    auth/
      __init__.py
      router.py
      schemas.py
      services.py
```

Near-term additions after the first slice should expand this into:

```text
blog/api/
  compatibility/
  shared/
  auth/
  posts/
  comments/
  tags/
  users/
  dashboard/
```

### Keep vs change decisions

Keep in phase 1:

- public route paths
- response payload shapes
- session-cookie auth model
- CSRF cookie/header contract
- custom pagination envelope
- DRF serializers as the source of truth for compatibility-sensitive output where that reduces risk

Change in phase 1:

- create a dedicated Ninja package
- define explicit auth-focused schemas and helpers
- separate preview migration code from the legacy DRF file
- introduce a migration seam that can later absorb throttling, error normalization, and shared permissions

Change later, not in phase 1:

- route cleanup such as `/comments/{id}/delete/`
- pagination redesign
- global error format redesign
- one-root Ninja mount for the full public API

## TYS-173 First Slice

Start with auth foundation only.

The first slice should implement:

- Ninja auth package and router
- CSRF bootstrap endpoint
- current-user endpoint
- logout endpoint
- serializer-based compatibility helper for the current-user payload
- a preview mount under `/api/_ninja/auth/`

The first public cutover should then move these routes onto the same Ninja foundation:

- `/api/auth/csrf/`
- `/api/auth/user/`
- `/api/auth/logout/`

This proves:

- Ninja can coexist cleanly in the repo
- CSRF bootstrap can still set the expected cookie
- session-backed reads can return the current user payload correctly
- logout can run through the new stack

## Migration Sequencing

1. Define architecture, contracts, and guardrails
2. Stand up preview auth foundation in Ninja
3. Port shared auth, CSRF, throttle, and error helpers
4. Cut over public auth endpoints
5. Migrate read-only domains:
   - dashboard
   - posts GET
   - tags GET
   - users GET
   - comments GET
6. Migrate mutating content endpoints
7. Update backend tests away from DRF-specific assumptions
8. Update frontend integration and E2E coverage
9. Remove obsolete DRF API glue

## Benchmark Plan

Benchmark before public cutover and again after auth/read-only migration.

Representative measurements:

- p50 and p95 latency for:
  - `GET /api/auth/csrf/`
  - `GET /api/auth/user/`
  - `POST /api/auth/login/`
  - `GET /api/posts/`
  - `GET /api/dashboard/`
- SQL query counts on auth/user, posts list, post detail, and dashboard
- observed throttle behavior under burst load
- frontend-visible auth bootstrap behavior

Success criteria:

- no public contract regressions for migrated routes
- no auth/CSRF/security regression
- performance is at least neutral, with improvements as a bonus rather than a requirement

## Rollback Guardrails

- keep the current DRF public routes intact until parity is demonstrated
- migrate one domain at a time
- keep preview routes separate from public routes until tests prove parity
- never remove DRF auth code in the same change that introduces the preview Ninja replacement
- preserve all current frontend-critical fields and top-level keys until the frontend is intentionally updated

## Developer Notes

The migration foundation now lives in `blog/api/`.

The first internal preview surface should live under `/api/_ninja/auth/` so contributors can test the new stack safely without changing the production-facing contract yet.

## Skills Used

Local repo skills:

- `django-dev-ninja`
- `api-authentication`
- `django-security`
- `secure`

Project-scoped installed skills:

- `api-design-principles`
- `openapi-spec-generation`
- `api-designer`

These skills all supported the same decision: preserve the existing contract first, use explicit router/schema boundaries, and make compatibility choices deliberate instead of accidental.
