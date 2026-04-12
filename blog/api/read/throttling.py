"""
Django Ninja rate limits for the read API.

Uses ``ninja.throttling`` only. Limits come from Django setting
``NINJA_DEFAULT_THROTTLE_RATES`` (see ``config.settings.API_THROTTLE_RATES``).

Session-backed routes use ``request.user`` for auth; Ninja's ``AnonRateThrottle`` keys on ``request.auth`` instead, so anonymous throttling
uses a small custom class. Per-endpoint and global caps mirror ``blog.throttles``.
"""

from typing import Optional

from django.http import HttpRequest
from ninja.throttling import SimpleRateThrottle


class ReadAnonThrottle(SimpleRateThrottle):
    """Throttle anonymous clients by IP; skip when Django session user is authenticated."""

    scope = "anon"

    def get_cache_key(self, request: HttpRequest) -> Optional[str]:
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class ReadEndpointActorThrottle(SimpleRateThrottle):
    """Per URL name (or path) and per user or client IP."""

    scope = "endpoint_actor"

    def get_cache_key(self, request: HttpRequest) -> str:
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            actor = f"user:{user.pk}"
        else:
            actor = f"ip:{self.get_ident(request)}"

        resolver = getattr(request, "resolver_match", None)
        endpoint = resolver.view_name if resolver is not None else request.path
        ident = f"{endpoint}:{actor}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


class ReadGlobalAPIThrottle(SimpleRateThrottle):
    """Cross-endpoint cap per authenticated user or per anonymous IP."""

    scope = "api_global"

    def get_cache_key(self, request: HttpRequest) -> str:
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            ident = f"user:{user.pk}"
        else:
            ident = f"ip:{self.get_ident(request)}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


READ_API_THROTTLES = [
    ReadAnonThrottle(),
    ReadEndpointActorThrottle(),
    ReadGlobalAPIThrottle(),
]
