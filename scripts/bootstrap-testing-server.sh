#!/usr/bin/env bash
# Run from the directory that contains docker-compose.testing.yml and .env.testing
# (usually repo root, or /srv/blogit if you only deploy those files).
#
#   cd /path/to/that/directory
#   bash scripts/bootstrap-testing-server.sh testing-pr-42
#   bash scripts/bootstrap-testing-server.sh testing-pr-42-sha-abcdef123456 --force
#
# First argument is the GHCR image tag (testing-* only). Remaining args go to
# manage.py bootstrap_testing_server (e.g. --force).
#
# COMPOSE is optional: set when you need a different compose file or env path.
#
# Order: pull + up; migrate; bootstrap_testing_server.

set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "Usage: ${0##*/} <BLOGIT_TESTING_IMAGE_TAG> [bootstrap_testing_server args...]" >&2
  echo "  Example: ${0##*/} testing-pr-42" >&2
  echo "  Example: ${0##*/} testing-manual-sha-abcdef123456 --force" >&2
  exit 1
fi

export BLOGIT_TESTING_IMAGE_TAG="$1"
shift

COMPOSE="${COMPOSE:-docker compose -f docker-compose.testing.yml --env-file .env.testing}"

$COMPOSE pull
$COMPOSE up -d --wait
$COMPOSE exec blogit_backend python manage.py migrate --noinput
$COMPOSE exec blogit_backend python manage.py bootstrap_testing_server "$@"
