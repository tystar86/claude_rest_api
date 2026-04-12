import hashlib
import smtplib
import socket

from allauth.account.internal.flows.email_verification import (
    send_verification_email_for_user,
)
from allauth.account.utils import has_verified_email, setup_user_email
from django.conf import settings
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
from django.core.mail import BadHeaderError
from django.db import IntegrityError, transaction
from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from blog import api_views

from ninja import Router

from .schemas import CsrfTokenResponse, CurrentUserResponse, DetailResponse
from .services import (
    AUTHENTICATION_REQUIRED_DETAIL,
    compat_session_auth,
    attach_forced_user,
    json_compat_response,
    serialize_current_user,
)
from ..throttling import LOGIN_THROTTLES, RESEND_VERIFICATION_THROTTLES, WRITE_THROTTLES
from ..utils import request_data_or_error as _request_data_or_error

router = Router(tags=["Auth"])

_USER_LOOKUP_BY_EMAIL_ERRORS = (User.DoesNotExist, User.MultipleObjectsReturned)
_MAIL_SEND_ERRORS = (
    smtplib.SMTPException,
    BadHeaderError,
    socket.timeout,
    TimeoutError,
)


# ── Public auth (GET /csrf/ sets cookie; POST login/register require CSRF) ────


@router.api_operation(["GET", "HEAD"], "/csrf/", response=CsrfTokenResponse)
@ensure_csrf_cookie
def csrf_token(request: HttpRequest):
    return json_compat_response({"csrfToken": get_token(request)})


@router.post("/login/", throttle=LOGIN_THROTTLES)
@csrf_protect
def login(request: HttpRequest):
    attach_forced_user(request)
    data, error = _request_data_or_error(request)
    if error is not None:
        return error
    email = data.get("email", "")
    password = data.get("password", "")
    if not isinstance(email, str) or not isinstance(password, str):
        return json_compat_response({"detail": "Invalid credentials."}, status=400)

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
        return json_compat_response({"detail": "Invalid credentials."}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        api_views.security_log.warning(
            "Login failed: bad password for user_id=%s ip=%s",
            db_user.pk,
            request.META.get("REMOTE_ADDR"),
        )
        return json_compat_response({"detail": "Invalid credentials."}, status=400)

    if settings.ACCOUNT_EMAIL_VERIFICATION == "mandatory" and getattr(
        settings, "FEATURE_EMAIL_VERIFICATION_ROLLOUT", True
    ):
        if not has_verified_email(user):
            return json_compat_response(
                {
                    "detail": "Email address is not verified. Please check your inbox.",
                    "code": "email_not_verified",
                },
                status=403,
            )

    auth_login(request, user)
    return json_compat_response(serialize_current_user(user))


@router.post("/register/", throttle=WRITE_THROTTLES)
@csrf_protect
def register(request: HttpRequest):
    attach_forced_user(request)
    data, error = _request_data_or_error(request)
    if error is not None:
        return error
    email = data.get("email", "")
    username = data.get("username", "")
    password = data.get("password", "")
    if (
        not isinstance(email, str)
        or not isinstance(username, str)
        or not isinstance(password, str)
    ):
        return json_compat_response(
            {"detail": "email, username and password are required."},
            status=400,
        )
    email = email.strip().lower()
    username = username.strip()
    if not email or not username or not password.strip():
        return json_compat_response(
            {"detail": "email, username and password are required."},
            status=400,
        )
    if (
        User.objects.filter(email=email).exists()
        or User.objects.filter(username=username).exists()
    ):
        return json_compat_response({"detail": "Registration failed."}, status=400)

    try:
        with transaction.atomic():
            validate_password(password, user=None)
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
            )
            # Profile is created by accounts.signals.create_profile on User post_save.
    except ValidationError as exc:
        return json_compat_response({"password": exc.messages}, status=400)
    except IntegrityError:
        return json_compat_response({"detail": "Registration failed."}, status=400)
    if settings.ACCOUNT_EMAIL_VERIFICATION == "mandatory":
        setup_user_email(request, user, [])
        try:
            send_verification_email_for_user(request, user)
        except _MAIL_SEND_ERRORS:
            api_views.security_log.exception(
                "Failed to send verification email for user_id=%s; account created, resend required",
                user.pk,
            )
        return json_compat_response(
            {
                "detail": "Registration successful. Please check your email to verify your account.",
                "code": "verification_pending",
            },
            status=201,
        )

    auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return json_compat_response(serialize_current_user(user), status=201)


@router.post("/resend-verification/", throttle=RESEND_VERIFICATION_THROTTLES)
@csrf_protect
def resend_verification(request: HttpRequest):
    attach_forced_user(request)
    success_response = json_compat_response(
        {"detail": "Verification email sent. Please check your inbox."}
    )
    is_anonymous_request = not request.user.is_authenticated

    user = None
    if not is_anonymous_request:
        user = request.user
    else:
        data, error = _request_data_or_error(request)
        if error is not None:
            return error
        email = data.get("email", "")
        if not isinstance(email, str):
            return success_response
        email = email.strip().lower()
        if email:
            try:
                user = User.objects.get(email=email)
            except _USER_LOOKUP_BY_EMAIL_ERRORS:
                pass

    if user is None:
        return success_response

    if has_verified_email(user):
        return success_response

    setup_user_email(request, user, [])
    if is_anonymous_request:
        try:
            send_verification_email_for_user(request, user)
        except _MAIL_SEND_ERRORS:
            api_views.security_log.exception(
                "Failed to resend verification email for user_id=%s",
                user.pk,
            )
            return success_response
    else:
        try:
            send_verification_email_for_user(request, user)
        except _MAIL_SEND_ERRORS:
            api_views.security_log.exception(
                "Failed to resend verification email for user_id=%s",
                user.pk,
            )
            return json_compat_response(
                {
                    "detail": "Failed to send verification email. Please try again later."
                },
                status=500,
            )

    return success_response


# ── Authenticated + CSRF-protected ────────────────────────────────────────────


@router.api_operation(
    ["GET", "HEAD"],
    "/user/",
    auth=compat_session_auth,
    response={200: CurrentUserResponse, 403: DetailResponse},
)
def current_user(request: HttpRequest):
    user = getattr(request, "auth", None) or request.user
    return json_compat_response(serialize_current_user(user))


@router.post("/logout/", auth=compat_session_auth, response=DetailResponse)
@csrf_protect
def logout_view(request: HttpRequest):
    if getattr(request.user, "is_authenticated", False):
        logout(request)
    return json_compat_response({"detail": "Logged out."})


@router.patch("/profile/", throttle=WRITE_THROTTLES)
@csrf_protect
def update_profile(request: HttpRequest):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response(
            {"detail": AUTHENTICATION_REQUIRED_DETAIL},
            status=401,
        )

    user = request.user
    data, error = _request_data_or_error(request)
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
            elif (
                User.objects.filter(username=new_username).exclude(id=user.id).exists()
            ):
                errors["username"] = "Username already taken."
            else:
                user.username = new_username

    if new_password is not None:
        if not isinstance(new_password, str):
            errors["new_password"] = "Password must be a string."
        elif not current_password:
            errors["current_password"] = (
                "Current password is required to change password."
            )
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
        return json_compat_response(errors, status=400)

    user.save()
    if password_changed:
        update_session_auth_hash(request, user)

    return json_compat_response(serialize_current_user(user))
