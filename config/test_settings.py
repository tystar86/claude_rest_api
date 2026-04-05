"""Test settings — identical to production settings but with an in-memory SQLite
database so unit tests run without a PostgreSQL server or libpq installed."""

import os

# Ensure .env.testing is loaded before importing the base settings.
os.environ.setdefault("DJANGO_ENV", "testing")

from config.settings import *  # noqa: E402, F401, F403, F405

# Override the database with fast, zero-dependency SQLite.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable caching in tests so every test hits the DB directly and cached
# results from one test cannot bleed into another running in the same worker.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}
