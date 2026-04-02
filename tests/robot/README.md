# Robot Framework Tests

This folder contains Robot Framework test suites for:

- backend API tests (`tests/robot/api`)
- frontend UI tests (`tests/robot/ui`)

## Prerequisites

- Backend running on `http://localhost:8000`
- Frontend running on `http://localhost:5173`

## Install dependencies

From repo root:

```bash
uv sync --group dev
uv run rfbrowser init
```

## Run all Robot tests

```bash
uv run robot tests/robot
```

## Run only API tests

```bash
uv run robot tests/robot/api
```

## Run only UI tests

```bash
uv run robot tests/robot/ui
```

## Notes

- UI tests use Robot Framework Browser library (Playwright engine).
- `post_detail_navigation.robot` expects at least one post to exist.
