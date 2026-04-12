"""
Unified Django Ninja rate limits for all API surfaces.

Rates come from ``NINJA_DEFAULT_THROTTLE_RATES`` (aliased from
``API_THROTTLE_RATES`` in ``config.settings``).
"""

from typing import Optional

from django.http import HttpRequest
from ninja.throttling import SimpleRateThrottle


class AnonThrottle(SimpleRateThrottle):
    scope = "anon"

    def get_cache_key(self, request: HttpRequest) -> Optional[str]:
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class UserThrottle(SimpleRateThrottle):
    scope = "user"

    def get_cache_key(self, request: HttpRequest) -> Optional[str]:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": user.pk,
        }


class EndpointActorThrottle(SimpleRateThrottle):
    scope = "endpoint_actor"

    def get_cache_key(self, request: HttpRequest) -> str:
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            actor = f"user:{user.pk}"
        else:
            actor = f"ip:{self.get_ident(request)}"

        resolver = getattr(request, "resolver_match", None)
        route = getattr(resolver, "route", None) if resolver is not None else None
        view_name = resolver.view_name if resolver is not None else None
        url_name = resolver.url_name if resolver is not None else None
        endpoint = route or view_name or url_name or request.path
        ident = f"{endpoint}:{actor}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


class GlobalAPIThrottle(SimpleRateThrottle):
    scope = "api_global"

    def get_cache_key(self, request: HttpRequest) -> str:
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            ident = f"user:{user.pk}"
        else:
            ident = f"ip:{self.get_ident(request)}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


class LoginThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request: HttpRequest) -> str:
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class ResendVerificationThrottle(SimpleRateThrottle):
    scope = "resend_verification"

    def get_cache_key(self, request: HttpRequest) -> str:
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            ident = f"user:{user.pk}"
        else:
            ident = f"ip:{self.get_ident(request)}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


# Pre-built throttle lists referenced by routers.
READ_THROTTLES = [AnonThrottle(), EndpointActorThrottle(), GlobalAPIThrottle()]

WRITE_THROTTLES = [
    AnonThrottle(),
    UserThrottle(),
    EndpointActorThrottle(),
    GlobalAPIThrottle(),
]

LOGIN_THROTTLES = [LoginThrottle(), *WRITE_THROTTLES]

RESEND_VERIFICATION_THROTTLES = [
    ResendVerificationThrottle(),
    *WRITE_THROTTLES,
]
