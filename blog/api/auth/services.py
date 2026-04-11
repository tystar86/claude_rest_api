from django.http import JsonResponse
from ninja.security import SessionAuth

from blog.serializers import CurrentUserSerializer


AUTHENTICATION_REQUIRED_DETAIL = "Authentication credentials were not provided."


class CompatSessionAuth(SessionAuth):
    """Honor Django sessions in production and DRF force_authenticate in tests."""

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


def serialize_current_user(user) -> dict:
    return dict(CurrentUserSerializer(user).data)
