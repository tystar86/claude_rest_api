# Frontend Guide

## Stack

- React 19
- React Router 7
- Vite 8
- Axios
- Bootstrap 5 plus a custom theme layer in `frontend/src/styles/theme.css`

## Entry Points

- `frontend/src/main.jsx`: bootstraps React, React Router, Bootstrap CSS, Bootstrap Icons, and the custom theme
- `frontend/src/App.jsx`: declares the route tree and wraps the app in `AuthProvider`

## Route Map

Routes are declared directly in `frontend/src/App.jsx`:

- `/dashboard`
- `/comments`
- `/posts`
- `/posts/:slug`
- `/tags`
- `/tags/:slug`
- `/users`
- `/users/:username`
- `/profile`
- `/login`
- `/register`

The root route redirects to `/dashboard`.

## How Data Fetching Works

The frontend does not use a separate data-fetching library.

Instead:

- All API helpers live in `frontend/src/api/client.js`
- Pages call those helpers directly
- Local component state handles loading, errors, pagination, and optimistic UI decisions

This keeps the app simple, but also means:

- State management is page-local
- There is no shared cache layer
- Cross-page data consistency is handled manually

## CSRF and Auth Bootstrap

`frontend/src/api/client.js` is one of the most important files for new contributors.

It handles:

- Axios instance creation
- `withCredentials: true` for Django session cookies
- CSRF token bootstrap from `/api/auth/csrf/`
- Automatic `X-CSRFToken` injection on write requests

`frontend/src/context/AuthContext.jsx` then:

- fetches CSRF once on app startup
- fetches the current user
- exposes `user`, `setUser`, `logout`, and `loading`

## Page Structure

Most route files in `frontend/src/pages/` are self-contained screens.

Examples:

- `Dashboard.jsx`: dashboard aggregates and summary cards
- `PostList.jsx`: post list, create flow, and tag loading
- `PostDetail.jsx`: post detail, edit flow, comment tree, voting, and replies
- `TagList.jsx`: tag CRUD for users with tag-management privileges
- `UserProfile.jsx`: profile updates and password changes
- `Login.jsx` and `Register.jsx`: email/password registration and login

Important note:

- `PostDetail.jsx` and `PostList.jsx` carry more page-level logic than the rest of the frontend
- Those are the first places to inspect when comment/post flows change

## Shared UI Pieces

Reusable components live in `frontend/src/components/`:

- `Navbar.jsx`
- `Pagination.jsx`
- `RoleBadge.jsx`
- `StatusBadge.jsx`

The app leans on Bootstrap classes for layout and components, then overrides their look through the custom CSS theme.

Current repo note:

- `Pagination.jsx` exists, but the main pages currently use bespoke "Load More" flows instead of importing it

## Styling Model

The styling system is:

1. Bootstrap base CSS
2. Bootstrap Icons font
3. `frontend/src/styles/theme.css` overrides and custom classes

Theme characteristics:

- Space Grotesk and Space Mono typography
- hard borders and shadows
- flat neo-brutalist-inspired component treatment

When changing UI:

- Prefer staying within the existing Bootstrap-plus-theme pattern
- Avoid introducing a second component framework

## Environment and Deployment

### Local dev

The frontend defaults to:

- `http://localhost:5173`
- backend API at `http://localhost:8000/api` unless `VITE_API_URL` is set

### Production

- The production frontend image is `frontend/Dockerfile.frontend.production`
- The production frontend is served by nginx inside the container and proxied by Caddy
- Production should use same-origin `/api` calls; `VITE_API_URL` can still override that when needed
- For whole-stack VPS or test-server planning, see `docs/deployment/test-server-deployment-plan.md`

## Frontend Tests

Current test setup:

- Vitest runs through `frontend/vite.config.js`
- `jsdom` is the test environment
- `frontend/src/test/setup.js` loads `@testing-library/jest-dom`
- route and API modules are mocked from `frontend/src/test/mocks/`

Current test coverage is light and focused on:

- `Dashboard.test.jsx`
- `Login.test.jsx`
- `Register.test.jsx`

Cross-stack UI behavior is covered separately by Robot Framework suites in `tests/robot/ui/`.

## Frontend Conventions

- Put route screens in `frontend/src/pages/`
- Put shared presentational pieces in `frontend/src/components/`
- Put HTTP helpers in `frontend/src/api/`
- Keep auth/session bootstrap in `frontend/src/context/`
- Use npm scripts from `frontend/package.json` for lint, test, build, and preview

## Useful Source Files

- `frontend/src/main.jsx`
- `frontend/src/App.jsx`
- `frontend/src/api/client.js`
- `frontend/src/context/AuthContext.jsx`
- `frontend/src/components/Navbar.jsx`
- `frontend/src/pages/PostList.jsx`
- `frontend/src/pages/PostDetail.jsx`
- `frontend/src/pages/UserProfile.jsx`
- `frontend/src/styles/theme.css`
- `frontend/vite.config.js`
- `frontend/eslint.config.js`
