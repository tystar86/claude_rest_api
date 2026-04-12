from django.http import JsonResponse
from ninja.security import SessionAuth

from blog.serializers import CurrentUserSerializer


AUTHENTICATION_REQUIRED_DETAIL = "Authentication credentials were not provided."


class CompatSessionAuth(SessionAuth):
    """Honor Django sessions and support test-level force_login."""

    def authenticate(self, request, key):
        user = super().authenticate(request, key)
        if user is not None:
            return user
        return getattr(request, "_force_auth_user", None)


compat_session_auth = CompatSessionAuth()


def json_compat_response(payload: dict, *, status: int = 200) -> JsonResponse:
    response = JsonResponse(payload, status=status)
    response.data = payload
    return response


def empty_compat_response(*, status: int) -> JsonResponse:
    if status == 404:
        payload = {"detail": "Not found."}
        response = JsonResponse(payload, status=status)
        response.data = payload
    else:
        response = JsonResponse({}, status=status)
    return response


def attach_forced_user(request):
    if getattr(request.user, "is_authenticated", False):
        return request.user
    forced_user = getattr(request, "_force_auth_user", None)
    if forced_user is not None:
        request.user = forced_user
        return forced_user
    return request.user


def serialize_current_user(user) -> dict:
    return dict(CurrentUserSerializer(user).data)
