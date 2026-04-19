import hashlib

from django.contrib.auth import (
    authenticate,
    login as auth_login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpRequest, JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from blog import api_views
from blog.serializers import CurrentUserSerializer
from ninja import Router
from ninja.security import SessionAuth

from ..constants import AUTHENTICATION_REQUIRED_DETAIL
from .schemas import CsrfTokenResponse, CurrentUserResponse, DetailResponse
from ..throttling import LOGIN_THROTTLES, WRITE_THROTTLES
from ..utils import request_data_or_error

router = Router(tags=["Auth"])
compat_session_auth = SessionAuth()
_USER_LOOKUP_BY_EMAIL_ERRORS = (User.DoesNotExist, User.MultipleObjectsReturned)


# ── Public auth (GET /csrf/ sets cookie; POST login/register require CSRF) ────


@router.api_operation(["GET", "HEAD"], "/csrf/", response=CsrfTokenResponse)
@ensure_csrf_cookie
def csrf_token(request: HttpRequest):
    return JsonResponse({"csrfToken": get_token(request)}, status=200)


@router.post("/login/", throttle=LOGIN_THROTTLES)
@csrf_protect
def login(request: HttpRequest):
    data, error = request_data_or_error(request)
    if error is not None:
        return error
    email = data.get("email", "")
    password = data.get("password", "")
    if not isinstance(email, str) or not isinstance(password, str):
        return JsonResponse({"detail": "Invalid credentials."}, status=400)

    email = email.strip().lower()
    try:
        db_user = User.objects.get(email=email)
        username = db_user.username
    except _USER_LOOKUP_BY_EMAIL_ERRORS:
        check_password(password, api_views._DUMMY_PASSWORD_HASH)
        email_fp = hashlib.sha256(email.lower().strip().encode()).hexdigest()[:16]
        api_views.security_log.warning(
            "Login failed: unknown email_fp=%s ip=%s",
            email_fp,
            request.META.get("REMOTE_ADDR"),
        )
        return JsonResponse({"detail": "Invalid credentials."}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        api_views.security_log.warning(
            "Login failed: bad password for user_id=%s ip=%s",
            db_user.pk,
            request.META.get("REMOTE_ADDR"),
        )
        return JsonResponse({"detail": "Invalid credentials."}, status=400)

    auth_login(request, user)
    return JsonResponse(dict(CurrentUserSerializer(user).data), status=200)


@router.post("/register/", throttle=WRITE_THROTTLES)
@csrf_protect
def register(request: HttpRequest):
    data, error = request_data_or_error(request)
    if error is not None:
        return error
    email = data.get("email", "")
    username = data.get("username", "")
    password = data.get("password", "")
    if not isinstance(email, str) or not isinstance(username, str) or not isinstance(password, str):
        return JsonResponse({"detail": "email, username and password are required."}, status=400)

    email = email.strip().lower()
    username = username.strip()
    if not email or not username or not password.strip():
        return JsonResponse(
            {"detail": "email, username and password are required."},
            status=400,
        )
    if User.objects.filter(email=email).exists() or User.objects.filter(username=username).exists():
        return JsonResponse({"detail": "Registration failed."}, status=400)

    try:
        with transaction.atomic():
            candidate_user = User(username=username, email=email)
            validate_password(password, candidate_user)
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
            )
    except ValidationError as exc:
        return JsonResponse({"password": exc.messages}, status=400)
    except IntegrityError:
        return JsonResponse({"detail": "Registration failed."}, status=400)

    auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return JsonResponse(dict(CurrentUserSerializer(user).data), status=201)


# ── Authenticated + CSRF-protected ────────────────────────────────────────────


@router.api_operation(
    ["GET", "HEAD"],
    "/user/",
    auth=compat_session_auth,
    response={200: CurrentUserResponse, 403: DetailResponse},
)
def current_user(request: HttpRequest):
    user = getattr(request, "auth", None) or request.user
    return JsonResponse(dict(CurrentUserSerializer(user).data), status=200)


@router.post("/logout/", auth=compat_session_auth, response=DetailResponse)
@csrf_protect
def logout_view(request: HttpRequest):
    if getattr(request.user, "is_authenticated", False):
        logout(request)
    return JsonResponse({"detail": "Logged out."}, status=200)


@router.patch("/profile/", throttle=WRITE_THROTTLES)
@csrf_protect
def update_profile(request: HttpRequest):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": AUTHENTICATION_REQUIRED_DETAIL}, status=401)

    user = request.user
    data, error = request_data_or_error(request)
    if error is not None:
        return error
    new_username = data.get("username")
    current_password = data.get("current_password")
    new_password = data.get("new_password")

    errors = {}
    password_changed = False

    if new_username is not None:
        if not isinstance(new_username, str):
            errors["username"] = "Username must be a string."
        else:
            new_username = new_username.strip()
            if not new_username:
                errors["username"] = "Username cannot be empty."
            elif User.objects.filter(username=new_username).exclude(id=user.id).exists():
                errors["username"] = "Username already taken."
            else:
                user.username = new_username

    if new_password is not None:
        if not isinstance(new_password, str):
            errors["new_password"] = "Password must be a string."
        elif not current_password:
            errors["current_password"] = "Current password is required to change password."
        elif not isinstance(current_password, str):
            errors["current_password"] = "Current password must be a string."
        elif not user.check_password(current_password):
            errors["current_password"] = "Current password is incorrect."
        else:
            try:
                validate_password(new_password, user)
            except ValidationError as exc:
                errors["new_password"] = list(exc.messages)
            else:
                user.set_password(new_password)
                password_changed = True

    if errors:
        return JsonResponse(errors, status=400)

    try:
        user.save()
    except IntegrityError:
        return JsonResponse(
            {"username": "Username already taken."},
            status=400,
        )
    if password_changed:
        update_session_auth_hash(request, user)

    return JsonResponse(dict(CurrentUserSerializer(user).data), status=200)
