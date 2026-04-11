from django.contrib.auth import logout
from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from ninja import Router

from .schemas import CsrfTokenResponse, CurrentUserResponse, DetailResponse
from .services import compat_session_auth, json_compat_response, serialize_current_user

router = Router(tags=["Auth Preview"])


@router.get("/csrf/", response=CsrfTokenResponse)
@csrf_exempt
@ensure_csrf_cookie
def csrf_preview(request: HttpRequest):
    return json_compat_response({"csrfToken": get_token(request)})


@router.get(
    "/user/",
    auth=compat_session_auth,
    response={200: CurrentUserResponse, 403: DetailResponse},
)
def current_user_preview(request: HttpRequest):
    user = getattr(request, "auth", None) or request.user
    return json_compat_response(serialize_current_user(user))


@router.post("/logout/", auth=compat_session_auth, response=DetailResponse)
@csrf_protect
def logout_preview(request: HttpRequest):
    if getattr(request.user, "is_authenticated", False):
        logout(request)
    return json_compat_response({"detail": "Logged out."})
