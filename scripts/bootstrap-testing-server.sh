#!/usr/bin/env bash
# Run from the directory that contains docker-compose.testing.yml and .env.testing
# (usually repo root, or /srv/blogit if you only deploy those files).
#
#   cd /path/to/that/directory
#   bash /path/to/scripts/bootstrap-testing-server.sh
#   bash /path/to/scripts/bootstrap-testing-server.sh --force
#
# COMPOSE is optional: the line below is the default. Set COMPOSE only when you need
# a different compose file or env path, e.g. COMPOSE='docker compose -f other.yml ...' bash ...
#
# Order: pull + up; migrate; bootstrap_testing_server (pass through --force etc. via "$@").

set -euo pipefail
COMPOSE="${COMPOSE:-docker compose -f docker-compose.testing.yml --env-file .env.testing}"

$COMPOSE pull
$COMPOSE up -d --wait
$COMPOSE exec blogit_backend python manage.py migrate --noinput
$COMPOSE exec blogit_backend python manage.py bootstrap_testing_server "$@"
