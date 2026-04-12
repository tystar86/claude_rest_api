"""
Django Ninja rate limits for the write API.

Uses ``ninja.throttling`` only. Limits come from Django setting
``NINJA_DEFAULT_THROTTLE_RATES`` (see ``config.settings.API_THROTTLE_RATES``).
The stack mirrors DRF defaults used by the legacy write handlers.
"""

from typing import Optional

from django.http import HttpRequest
from ninja.throttling import SimpleRateThrottle


class WriteAnonThrottle(SimpleRateThrottle):
    """Throttle anonymous clients by IP; skip authenticated users."""

    scope = "anon"

    def get_cache_key(self, request: HttpRequest) -> Optional[str]:
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class WriteUserThrottle(SimpleRateThrottle):
    """Throttle authenticated users by user id."""

    scope = "user"

    def get_cache_key(self, request: HttpRequest) -> Optional[str]:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": user.pk,
        }


class WriteEndpointActorThrottle(SimpleRateThrottle):
    """Per URL name (or path) and per user or client IP."""

    scope = "endpoint_actor"

    def get_cache_key(self, request: HttpRequest) -> str:
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            actor = f"user:{user.pk}"
        else:
            actor = f"ip:{self.get_ident(request)}"

        resolver = getattr(request, "resolver_match", None)
        view_name = resolver.view_name if resolver is not None else None
        endpoint = view_name if view_name else request.path
        ident = f"{endpoint}:{actor}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


class WriteGlobalAPIThrottle(SimpleRateThrottle):
    """Cross-endpoint cap per authenticated user or per anonymous IP."""

    scope = "api_global"

    def get_cache_key(self, request: HttpRequest) -> str:
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            ident = f"user:{user.pk}"
        else:
            ident = f"ip:{self.get_ident(request)}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


WRITE_API_THROTTLES = [
    WriteAnonThrottle(),
    WriteUserThrottle(),
    WriteEndpointActorThrottle(),
    WriteGlobalAPIThrottle(),
]
