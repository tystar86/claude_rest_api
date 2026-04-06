import os
from pathlib import Path
from typing import Any

import dj_database_url

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv(f".env.{os.environ.get('DJANGO_ENV', 'local')}")

BASE_DIR: Path = Path(__file__).resolve().parent.parent

SECRET_KEY: str = os.environ["SECRET_KEY"]

DEBUG: bool = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS: list[str] = [
    h for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h
]

INSTALLED_APPS: list[str] = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "anymail",
    # allauth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    # local
    "blog",
    "accounts",
]

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
    "allauth.account.middleware.AccountMiddleware",
]

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
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID: int = 1

# django-allauth
ACCOUNT_LOGIN_METHODS: set[str] = {"email"}
ACCOUNT_SIGNUP_FIELDS: list[str] = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION: str = os.environ.get(
    "ACCOUNT_EMAIL_VERIFICATION", "mandatory"
)
# When False, login_view skips the mandatory-verification gate so existing
# users aren't locked out before a backfill has run.  Default True (enforce).
FEATURE_EMAIL_VERIFICATION_ROLLOUT: bool = (
    os.environ.get("FEATURE_EMAIL_VERIFICATION_ROLLOUT", "true").lower() == "true"
)
LOGIN_REDIRECT_URL: str = os.environ.get(
    "LOGIN_REDIRECT_URL", "http://localhost:5173/dashboard"
)
LOGOUT_REDIRECT_URL: str = os.environ.get(
    "LOGOUT_REDIRECT_URL", "http://localhost:5173/dashboard"
)
ACCOUNT_DEFAULT_HTTP_PROTOCOL: str = os.environ.get(
    "ACCOUNT_DEFAULT_HTTP_PROTOCOL", "http"
)
SOCIALACCOUNT_LOGIN_ON_GET: bool = False
SOCIALACCOUNT_PROVIDERS: dict[str, Any] = {
    "google": {
        "APP": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

WSGI_APPLICATION: str = "config.wsgi.application"

DATABASES: dict[str, Any] = {
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
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE: str = "en-us"
TIME_ZONE: str = "UTC"
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

# Security
X_FRAME_OPTIONS: str = os.environ.get("X_FRAME_OPTIONS", "DENY")
SECURE_CONTENT_TYPE_NOSNIFF: bool = True
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

# DRF
REST_FRAMEWORK: dict[str, Any] = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "blog.throttles.BurstAnonThrottle",
        "blog.throttles.BurstUserThrottle",
        "blog.throttles.EndpointActorThrottle",
        "blog.throttles.GlobalAPIThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # Per anonymous IP across API
        "anon": os.environ.get("DRF_THROTTLE_ANON") or "120/min",
        # Per authenticated user across API
        "user": os.environ.get("DRF_THROTTLE_USER") or "240/min",
        # Per endpoint + per actor (user or IP)
        "endpoint_actor": os.environ.get("DRF_THROTTLE_ENDPOINT_ACTOR") or "60/min",
        # Overall global API cap
        "api_global": os.environ.get("DRF_THROTTLE_API_GLOBAL") or "1000/min",
        # Login endpoint brute-force protection (per IP)
        "login": os.environ.get("DRF_THROTTLE_LOGIN") or "5/min",
    },
}

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


# Email — console backend locally, Mailgun via anymail in production
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@yourdomain.com")
ANYMAIL: dict[str, Any] = {
    "MAILGUN_API_KEY": os.environ.get("MAILGUN_API_KEY", ""),
    "MAILGUN_SENDER_DOMAIN": os.environ.get("MAILGUN_DOMAIN", ""),
}
