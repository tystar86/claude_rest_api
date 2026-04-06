from rest_framework.throttling import (
    AnonRateThrottle,
    SimpleRateThrottle,
    UserRateThrottle,
)


class EndpointActorThrottle(SimpleRateThrottle):
    """
    Per-endpoint + per-actor throttle.
    Actor is authenticated user ID or client IP for anonymous requests.
    """

    scope = "endpoint_actor"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            actor = f"user:{request.user.pk}"
        else:
            actor = f"ip:{self.get_ident(request)}"

        resolver = getattr(request, "resolver_match", None)
        endpoint = resolver.view_name if resolver is not None else request.path
        ident = f"{endpoint}:{actor}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


class GlobalAPIThrottle(SimpleRateThrottle):
    """
    Cross-endpoint throttle per actor across the whole API.
    """

    scope = "api_global"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = f"user:{request.user.pk}"
        else:
            ident = f"ip:{self.get_ident(request)}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


class BurstAnonThrottle(AnonRateThrottle):
    scope = "anon"


class BurstUserThrottle(UserRateThrottle):
    scope = "user"


class LoginRateThrottle(SimpleRateThrottle):
    """Tight per-IP throttle for the login endpoint to prevent brute force."""

    scope = "login"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
