import os
import sys
from pathlib import Path
from typing import Any

import dj_database_url

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


def _default_django_env() -> str:
    argv0 = Path(sys.argv[0]).name.lower()
    if "pytest" in argv0:
        return "testing"
    return "local"


DJANGO_ENV = os.environ.get("DJANGO_ENV", _default_django_env())
os.environ.setdefault("DJANGO_ENV", DJANGO_ENV)
load_dotenv(f".env.{DJANGO_ENV}")
TEST_USE_POSTGRES = os.environ.get("TEST_USE_POSTGRES", "False").lower() == "true"

# django-silk: ENABLE_SILK = True only (never in pytest "testing" unless explicitly forced).
ENABLE_SILK: bool = os.environ.get("ENABLE_SILK", "False").lower() == "true"
SILKY_PYTHON_PROFILER: bool = os.environ.get("SILKY_PYTHON_PROFILER", "False").lower() == "true"

BASE_DIR: Path = Path(__file__).resolve().parent.parent

SECRET_KEY: str = os.environ["SECRET_KEY"]

DEBUG: bool = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS: list[str] = [h for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h]

INSTALLED_APPS: list[str] = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "corsheaders",
    # local
    "blog",
    "accounts",
]
if ENABLE_SILK:
    INSTALLED_APPS.insert(INSTALLED_APPS.index("corsheaders") + 1, "silk")

AUTH_USER_MODEL = "accounts.CustomUser"

MIDDLEWARE: list[str | None] = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "blog.api.csrf.JsonMethodNotAllowedMiddleware",
]
if ENABLE_SILK:
    _csrf_i = MIDDLEWARE.index("django.middleware.csrf.CsrfViewMiddleware")
    MIDDLEWARE.insert(_csrf_i, "silk.middleware.SilkyMiddleware")

ROOT_URLCONF: str = "config.urls"

TEMPLATES: list[dict[str, Any]] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

AUTHENTICATION_BACKENDS: list[str | None] = [
    "django.contrib.auth.backends.ModelBackend",
]

SITE_ID: int = 1

WSGI_APPLICATION: str = "config.wsgi.application"

if DJANGO_ENV == "testing" and not TEST_USE_POSTGRES:
    DATABASES: dict[str, Any] = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
else:
    DATABASES = {
        "default": dj_database_url.config(
            default="postgresql://{}:{}@{}:{}/{}".format(
                os.environ["DB_USER"],
                os.environ["DB_PASSWORD"],
                os.environ.get("DB_HOST", "localhost"),
                os.environ.get("DB_PORT", "5432"),
                os.environ["DB_NAME"],
            ),
            conn_max_age=int(os.environ.get("DB_CONN_MAX_AGE", 60)),
        )
    }
    # Validate persistent connections before reuse to avoid "connection already
    # closed" errors with long-lived workers (Django 4.1+).
    # Only has effect when DB_CONN_MAX_AGE > 0.
    DATABASES["default"].setdefault(
        "CONN_HEALTH_CHECKS", os.environ.get("CONN_HEALTH_CHECKS", "True") == "True"
    )

AUTH_PASSWORD_VALIDATORS: list[dict[str, Any]] = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE: str = "en-us"
TIME_ZONE: str = "Europe/Prague"
USE_I18N: bool = True
USE_TZ: bool = True

STATIC_URL: str = "static/"
STATIC_ROOT: Path = BASE_DIR / "staticfiles"

STORAGES: dict[str, Any] = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD: str = "django.db.models.BigAutoField"

# `bootstrap_testing_server` — disposable test-VPS superuser (set in `.env.testing`).
TESTING_BOOTSTRAP_SUPERUSER_USERNAME: str = os.environ.get(
    "TESTING_BOOTSTRAP_SUPERUSER_USERNAME", "testing"
)
TESTING_BOOTSTRAP_SUPERUSER_EMAIL: str = os.environ.get(
    "TESTING_BOOTSTRAP_SUPERUSER_EMAIL", "testing@testing.com"
)
TESTING_BOOTSTRAP_SUPERUSER_PASSWORD: str = os.environ.get(
    "TESTING_BOOTSTRAP_SUPERUSER_PASSWORD", "testing"
)

# Security
CSRF_FAILURE_VIEW: str = "blog.api.csrf.csrf_failure_view"
X_FRAME_OPTIONS: str = os.environ.get("X_FRAME_OPTIONS", "DENY")
SECURE_CONTENT_TYPE_NOSNIFF: bool = True
# Trust the reverse proxy's forwarded scheme so HTTPS-terminated requests do not
# loop back through SECURE_SSL_REDIRECT when Django sits behind Caddy.
SECURE_PROXY_SSL_HEADER: tuple[str, str] = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT: bool = os.environ.get("SECURE_SSL_REDIRECT", "False") == "True"
SECURE_HSTS_SECONDS: int = int(os.environ.get("SECURE_HSTS_SECONDS", 0))
SECURE_HSTS_INCLUDE_SUBDOMAINS: bool = (
    os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False") == "True"
)
SECURE_HSTS_PRELOAD: bool = os.environ.get("SECURE_HSTS_PRELOAD", "False") == "True"
SESSION_COOKIE_SECURE: bool = os.environ.get("SESSION_COOKIE_SECURE", "False") == "True"
SESSION_COOKIE_HTTPONLY: bool = True
SESSION_COOKIE_AGE: int = int(os.environ.get("SESSION_COOKIE_AGE", 1209600))

_SAMESITE_ALLOWED = {"Lax", "Strict", "None"}
_samesite_raw = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SAMESITE: str = (
    _samesite_raw.capitalize() if _samesite_raw.lower() != "none" else "None"
)
if SESSION_COOKIE_SAMESITE not in _SAMESITE_ALLOWED:
    raise ImproperlyConfigured(
        f"SESSION_COOKIE_SAMESITE={_samesite_raw!r} is invalid. "
        f"Allowed values (case-insensitive): {sorted(_SAMESITE_ALLOWED)}."
    )
if SESSION_COOKIE_SAMESITE == "None" and not SESSION_COOKIE_SECURE:
    raise ImproperlyConfigured(
        "SESSION_COOKIE_SAMESITE='None' requires SESSION_COOKIE_SECURE=True "
        "or browsers will reject the cookie. Set SESSION_COOKIE_SECURE=True "
        "(HTTPS) or change SESSION_COOKIE_SAMESITE to 'Lax' or 'Strict'."
    )
CSRF_COOKIE_SECURE: bool = os.environ.get("CSRF_COOKIE_SECURE", "False") == "True"
_csrf_samesite_raw = os.environ.get("CSRF_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE: str = (
    _csrf_samesite_raw.capitalize() if _csrf_samesite_raw.lower() != "none" else "None"
)
if CSRF_COOKIE_SAMESITE not in _SAMESITE_ALLOWED:
    raise ImproperlyConfigured(
        f"CSRF_COOKIE_SAMESITE={_csrf_samesite_raw!r} is invalid. "
        f"Allowed values (case-insensitive): {sorted(_SAMESITE_ALLOWED)}."
    )
if CSRF_COOKIE_SAMESITE == "None" and not CSRF_COOKIE_SECURE:
    raise ImproperlyConfigured(
        "CSRF_COOKIE_SAMESITE='None' requires CSRF_COOKIE_SECURE=True "
        "or browsers will reject the cookie. Set CSRF_COOKIE_SECURE=True "
        "(HTTPS) or change CSRF_COOKIE_SAMESITE to 'Lax' or 'Strict'."
    )
CSRF_TRUSTED_ORIGINS: list[str] = [
    o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o
]
if DEBUG and not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

PASSWORD_HASHERS: list[str] = os.environ.get(
    "PASSWORD_HASHERS",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
).split(",")

# API rate limits for Django Ninja (`NINJA_DEFAULT_THROTTLE_RATES` / `API_THROTTLE_RATES`).
# Env names remain DRF_THROTTLE_* for existing deploys.
API_THROTTLE_RATES: dict[str, str] = {
    "anon": os.environ.get("DRF_THROTTLE_ANON") or "120/min",
    "user": os.environ.get("DRF_THROTTLE_USER") or "240/min",
    "endpoint_actor": os.environ.get("DRF_THROTTLE_ENDPOINT_ACTOR") or "60/min",
    "api_global": os.environ.get("DRF_THROTTLE_API_GLOBAL") or "1000/min",
    "login": os.environ.get("DRF_THROTTLE_LOGIN") or "5/min",
}

# Django Ninja reads this alias via ninja.conf.settings.DEFAULT_THROTTLE_RATES
NINJA_DEFAULT_THROTTLE_RATES: dict[str, str | None] = API_THROTTLE_RATES

# HTTP APIs are Django Ninja; throttling is configured via NINJA_DEFAULT_THROTTLE_RATES above.

# CORS
CORS_ALLOWED_ORIGINS: list[str] = [
    o for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o
]
if DEBUG and not CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
CORS_ALLOW_CREDENTIALS: bool = True
CSRF_COOKIE_HTTPONLY: bool = False  # React needs to read the CSRF cookie

if DJANGO_ENV == "testing":
    CACHES: dict[str, Any] = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }
    EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
    DEFAULT_FROM_EMAIL = "noreply@example.com"

# Security event logging
LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "security": {
            "format": "[%(asctime)s] %(levelname)s %(name)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "security",
        },
    },
    "loggers": {
        "security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

# Email — console by default; set EMAIL_BACKEND in the environment for production SMTP
# if needed. Skip these defaults in testing so the dummy backend above is not overwritten.
if DJANGO_ENV != "testing":
    EMAIL_BACKEND = os.environ.get(
        "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
    )
    DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@example.com")
