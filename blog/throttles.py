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

        endpoint = request.resolver_match.view_name or request.path
        ident = f"{endpoint}:{actor}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


class GlobalAPIThrottle(SimpleRateThrottle):
    """
    Global API throttle shared by all requests.
    """

    scope = "api_global"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": "global"}


class BurstAnonThrottle(AnonRateThrottle):
    scope = "anon"


class BurstUserThrottle(UserRateThrottle):
    scope = "user"
