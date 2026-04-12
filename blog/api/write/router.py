import json
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
    update_session_auth_hash,
)
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import BadHeaderError
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse
from ninja import Router

from accounts.models import Profile
from blog import api_views
from blog.models import Comment, CommentVote, Post, Tag
from blog.serializers import (
    CommentSerializer,
    PostDetailSerializer,
    PostWriteSerializer,
    TagSerializer,
)
from blog.utils import build_unique_slug

from ..auth.services import (
    AUTHENTICATION_REQUIRED_DETAIL,
    attach_forced_user,
    json_compat_response,
    serialize_current_user,
)
from .throttling import (
    WRITE_LOGIN_THROTTLES,
    WRITE_RESEND_VERIFICATION_THROTTLES,
)

router = Router(tags=["Write API"])


def _request_data(request: HttpRequest) -> dict:
    raw_body = getattr(request, "body", b"") or b"{}"
    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError:
        return {}
    if isinstance(data, dict):
        return data
    return {}


def _post_detail_queryset():
    return Post.objects.select_related("author").prefetch_related(
        "tags",
        "comments__author",
        "comments__votes",
        "comments__replies__author",
        "comments__replies__votes",
    )


@router.post("/auth/login/", throttle=WRITE_LOGIN_THROTTLES)
def login(request: HttpRequest):
    attach_forced_user(request)
    data = _request_data(request)
    email = data.get("email", "")
    password = data.get("password", "")
    if not isinstance(email, str) or not isinstance(password, str):
        return json_compat_response({"detail": "Invalid credentials."}, status=400)

    email = email.strip().lower()
    try:
        db_user = User.objects.get(email=email)
        username = db_user.username
    except (User.DoesNotExist, User.MultipleObjectsReturned):
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
                {"detail": "Email address is not verified. Please check your inbox."},
                status=403,
            )

    auth_login(request, user)
    return json_compat_response(serialize_current_user(user))


@router.post("/auth/register/")
def register(request: HttpRequest):
    attach_forced_user(request)
    data = _request_data(request)
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
    if not email or not username.strip() or not password.strip():
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
    except ValidationError as exc:
        return json_compat_response({"password": exc.messages}, status=400)
    except IntegrityError:
        return json_compat_response({"detail": "Registration failed."}, status=400)

    Profile.objects.get_or_create(user=user)
    if settings.ACCOUNT_EMAIL_VERIFICATION == "mandatory":
        setup_user_email(request, user, [])
        try:
            send_verification_email_for_user(request, user)
        except (smtplib.SMTPException, BadHeaderError, socket.timeout, TimeoutError):
            api_views.security_log.exception(
                "Failed to send verification email for user_id=%s; account created, resend required",
                user.pk,
            )
        return json_compat_response(
            {
                "detail": "Registration successful. Please check your email to verify your account."
            },
            status=201,
        )

    auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return json_compat_response(serialize_current_user(user), status=201)


@router.post("/auth/resend-verification/", throttle=WRITE_RESEND_VERIFICATION_THROTTLES)
def resend_verification(request: HttpRequest):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response({"detail": "Authentication required."}, status=401)

    user = request.user
    if has_verified_email(user):
        return json_compat_response(
            {"detail": "Email is already verified."}, status=400
        )

    setup_user_email(request, user, [])
    try:
        send_verification_email_for_user(request, user)
    except (smtplib.SMTPException, BadHeaderError, socket.timeout, TimeoutError):
        api_views.security_log.exception(
            "Failed to resend verification email for user_id=%s",
            user.pk,
        )
        return json_compat_response(
            {"detail": "Failed to send verification email. Please try again later."},
            status=500,
        )

    return json_compat_response(
        {"detail": "Verification email sent. Please check your inbox."}
    )


@router.patch("/auth/profile/")
def update_profile(request: HttpRequest):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response(
            {"detail": AUTHENTICATION_REQUIRED_DETAIL},
            status=403,
        )

    user = request.user
    data = _request_data(request)
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
            new_password = new_password.strip()
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


@router.post("/posts/")
def create_post(request: HttpRequest):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response(
            {"detail": "Authentication required."},
            status=401,
        )

    serializer = PostWriteSerializer(
        data=_request_data(request),
        context={"request": request},
    )
    if not serializer.is_valid():
        return json_compat_response(dict(serializer.errors), status=400)

    post = serializer.save()
    post = _post_detail_queryset().get(pk=post.pk)
    payload = PostDetailSerializer(post, context={"request": request}).data
    return json_compat_response(payload, status=201)


@router.patch("/posts/{slug}/")
def update_post(request: HttpRequest, slug: str):
    attach_forced_user(request)
    try:
        post = _post_detail_queryset().get(slug=slug)
    except Post.DoesNotExist:
        return HttpResponse(status=404)

    if not request.user.is_authenticated:
        return json_compat_response(
            {"detail": "Authentication required."},
            status=401,
        )

    if not api_views.can_view_unpublished_post(request.user, post):
        return json_compat_response(
            {"detail": "You can edit/delete only your own posts."},
            status=403,
        )

    serializer = PostWriteSerializer(
        post,
        data=_request_data(request),
        partial=True,
        context={"request": request},
    )
    if not serializer.is_valid():
        return json_compat_response(dict(serializer.errors), status=400)

    serializer.save()
    post = _post_detail_queryset().get(pk=post.pk)
    payload = PostDetailSerializer(post, context={"request": request}).data
    return json_compat_response(payload)


@router.delete("/posts/{slug}/")
def delete_post(request: HttpRequest, slug: str):
    attach_forced_user(request)
    try:
        post = _post_detail_queryset().get(slug=slug)
    except Post.DoesNotExist:
        return HttpResponse(status=404)

    if not request.user.is_authenticated:
        return json_compat_response(
            {"detail": "Authentication required."},
            status=401,
        )

    if not api_views.can_view_unpublished_post(request.user, post):
        return json_compat_response(
            {"detail": "You can edit/delete only your own posts."},
            status=403,
        )

    post.delete()
    return HttpResponse(status=204)


@router.post("/posts/{slug}/comments/")
def comment_create(request: HttpRequest, slug: str):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response(
            {"detail": AUTHENTICATION_REQUIRED_DETAIL}, status=403
        )

    data = _request_data(request)
    body = data.get("body")
    if body is not None and not isinstance(body, str):
        return json_compat_response(
            {"detail": "Comment body must be a string."}, status=400
        )
    body = (body or "").strip()
    if not body:
        return json_compat_response({"detail": "Comment body is required."}, status=400)

    try:
        post = Post.objects.get(slug=slug)
    except Post.DoesNotExist:
        return HttpResponse(status=404)
    if post.status != Post.Status.PUBLISHED and not api_views.can_view_unpublished_post(
        request.user, post
    ):
        return HttpResponse(status=404)

    parent_id = data.get("parent_id")
    parent = None
    if parent_id is not None:
        try:
            parent = Comment.objects.get(id=parent_id, post=post)
        except Comment.DoesNotExist:
            return json_compat_response(
                {"detail": "Parent comment not found."}, status=400
            )

    comment = Comment.objects.create(
        post=post,
        author=request.user,
        body=body,
        parent=parent,
        is_approved=True,
    )
    payload = CommentSerializer(comment, context={"request": request}).data
    return json_compat_response(payload, status=201)


@router.post("/tags/")
def create_tag(request: HttpRequest):
    attach_forced_user(request)
    if not api_views.can_manage_tags(request.user):
        return json_compat_response(
            {"detail": "Only moderators/admins can create tags."},
            status=403,
        )

    name = _request_data(request).get("name")
    if name is not None and not isinstance(name, str):
        return json_compat_response({"detail": "name must be a string."}, status=400)
    name = (name or "").strip().lower()
    if not name:
        return json_compat_response({"detail": "name is required."}, status=400)
    if Tag.objects.filter(name=name).exists():
        return json_compat_response({"detail": "Tag name already exists."}, status=400)

    try:
        tag = Tag.objects.create(name=name, slug=build_unique_slug(Tag, name))
    except IntegrityError:
        return json_compat_response({"detail": "Tag name already exists."}, status=400)

    return json_compat_response(dict(TagSerializer(tag).data), status=201)


@router.patch("/tags/{slug}/")
def update_tag(request: HttpRequest, slug: str):
    attach_forced_user(request)
    try:
        tag = Tag.objects.annotate(
            post_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
        ).get(slug=slug)
    except Tag.DoesNotExist:
        return HttpResponse(status=404)

    if not api_views.can_manage_tags(request.user):
        return json_compat_response(
            {"detail": "Only moderators/admins can manage tags."},
            status=403,
        )

    name = _request_data(request).get("name")
    if name is not None and not isinstance(name, str):
        return json_compat_response({"detail": "name must be a string."}, status=400)
    name = (name or "").strip().lower()
    if not name:
        return json_compat_response({"detail": "name is required."}, status=400)
    if Tag.objects.filter(name=name).exclude(id=tag.id).exists():
        return json_compat_response({"detail": "Tag name already exists."}, status=400)

    tag.name = name
    tag.slug = build_unique_slug(Tag, name, instance_id=tag.id)
    tag.save()
    return json_compat_response(dict(TagSerializer(tag).data))


@router.delete("/tags/{slug}/")
def delete_tag(request: HttpRequest, slug: str):
    attach_forced_user(request)
    try:
        tag = Tag.objects.annotate(
            post_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
        ).get(slug=slug)
    except Tag.DoesNotExist:
        return HttpResponse(status=404)

    if not api_views.can_manage_tags(request.user):
        return json_compat_response(
            {"detail": "Only moderators/admins can manage tags."},
            status=403,
        )

    tag.delete()
    return HttpResponse(status=204)


@router.post("/comments/{comment_id}/vote/")
def comment_vote(request: HttpRequest, comment_id: int):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response(
            {"detail": AUTHENTICATION_REQUIRED_DETAIL}, status=403
        )

    vote_type = _request_data(request).get("vote")
    if vote_type not in (CommentVote.VoteType.LIKE, CommentVote.VoteType.DISLIKE):
        return json_compat_response(
            {"detail": "vote must be 'like' or 'dislike'."},
            status=400,
        )

    try:
        comment = Comment.objects.select_related("post", "author").get(id=comment_id)
    except Comment.DoesNotExist:
        return HttpResponse(status=404)
    if not api_views.can_access_comment(request.user, comment):
        return HttpResponse(status=404)

    existing = CommentVote.objects.filter(comment=comment, user=request.user).first()
    if existing:
        if existing.vote == vote_type:
            existing.delete()
        else:
            existing.vote = vote_type
            existing.save()
    else:
        CommentVote.objects.create(comment=comment, user=request.user, vote=vote_type)

    comment.refresh_from_db()
    payload = CommentSerializer(comment, context={"request": request}).data
    return json_compat_response(payload)


@router.patch("/comments/{comment_id}/")
def comment_update(request: HttpRequest, comment_id: int):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response(
            {"detail": AUTHENTICATION_REQUIRED_DETAIL}, status=403
        )

    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        return HttpResponse(status=404)

    if comment.author_id != request.user.id:
        return json_compat_response(
            {"detail": "You can edit only your own comments."},
            status=403,
        )

    body = _request_data(request).get("body")
    if body is not None and not isinstance(body, str):
        return json_compat_response(
            {"detail": "Comment body must be a string."}, status=400
        )
    body = (body or "").strip()
    if not body:
        return json_compat_response({"detail": "Comment body is required."}, status=400)

    comment.body = body
    comment.save(update_fields=["body", "updated_at"])
    comment.refresh_from_db()
    payload = CommentSerializer(comment, context={"request": request}).data
    return json_compat_response(payload)


@router.delete("/comments/{comment_id}/delete/")
def comment_delete(request: HttpRequest, comment_id: int):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response(
            {"detail": AUTHENTICATION_REQUIRED_DETAIL}, status=403
        )

    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        return HttpResponse(status=404)

    if comment.author_id != request.user.id:
        return json_compat_response(
            {"detail": "You can delete only your own comments."},
            status=403,
        )

    comment.delete()
    return HttpResponse(status=204)
