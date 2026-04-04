from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from django.db.models import Count, Q

from accounts.models import Profile
from .models import Comment, CommentVote, Post, Tag
from .serializers import (
    CommentListSerializer,
    CommentSerializer,
    CurrentUserSerializer,
    PostDetailSerializer,
    PostSerializer,
    TagSerializer,
    UserSerializer,
)

PAGE_SIZE = 10
_MAX_PAGE = 10_000
# Dummy hash used for constant-time password check when user does not exist (prevents timing attacks).
_DUMMY_PASSWORD_HASH = make_password("_dummy_")


def paginate(qs, request, serializer_class):
    try:
        page = max(1, min(int(request.GET.get("page", 1)), _MAX_PAGE))
    except ValueError:
        page = 1
    total = qs.count()
    start = (page - 1) * PAGE_SIZE
    items = serializer_class(qs[start : start + PAGE_SIZE], many=True).data
    return {
        "count": total,
        "total_pages": max(1, -(-total // PAGE_SIZE)),
        "page": page,
        "results": items,
    }


def build_unique_slug(model_cls, source_text, instance_id=None):
    base = slugify(source_text or "").strip("-")[:50] or "item"
    candidate = base
    n = 2
    while True:
        qs = model_cls.objects.filter(slug=candidate)
        if instance_id is not None:
            qs = qs.exclude(id=instance_id)
        if not qs.exists():
            return candidate
        candidate = f"{base}-{n}"
        n += 1


def can_manage_tags(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    role = getattr(getattr(user, "profile", None), "role", "user")
    return role in ("moderator", "admin")


# ── Dashboard ──────────────────────────────────────────────────────────────────


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard(request):
    published = Post.objects.filter(status=Post.Status.PUBLISHED)
    total_posts = published.count()
    total_comments = Comment.objects.filter(post__status=Post.Status.PUBLISHED).count()
    total_authors = (
        User.objects.filter(posts__status=Post.Status.PUBLISHED).distinct().count()
    )
    active_tags = (
        Tag.objects.filter(posts__status=Post.Status.PUBLISHED).distinct().count()
    )

    bodies = published.values_list("body", flat=True)
    word_counts = [len((body or "").split()) for body in bodies]
    average_depth_words = (
        round(sum(word_counts) / len(word_counts)) if word_counts else 0
    )

    return Response(
        {
            "stats": {
                "total_posts": total_posts,
                "comments": total_comments,
                "authors": total_authors,
                "active_tags": active_tags,
                "average_depth_words": average_depth_words,
            },
            "latest_posts": PostSerializer(
                published.select_related("author")
                .prefetch_related("tags")
                .order_by("-created_at")[:10],
                many=True,
            ).data,
            "most_commented_posts": PostSerializer(
                published.select_related("author")
                .prefetch_related("tags")
                .annotate(comment_count=Count("comments"))
                .order_by("-comment_count")[:10],
                many=True,
            ).data,
            "most_used_tags": TagSerializer(
                Tag.objects.annotate(
                    post_count=Count(
                        "posts", filter=Q(posts__status=Post.Status.PUBLISHED)
                    )
                ).order_by("-post_count")[:10],
                many=True,
            ).data,
            "top_authors": UserSerializer(
                User.objects.select_related("profile")
                .annotate(
                    post_count=Count(
                        "posts", filter=Q(posts__status=Post.Status.PUBLISHED)
                    )
                )
                .filter(post_count__gt=0)
                .order_by("-post_count")[:10],
                many=True,
            ).data,
        }
    )


# ── Posts ──────────────────────────────────────────────────────────────────────


@api_view(["GET"])
@permission_classes([AllowAny])
def comment_list(request):
    qs = Comment.objects.select_related("author", "post").order_by("-created_at")
    return Response(paginate(qs, request, CommentListSerializer))


# ── Posts ──────────────────────────────────────────────────────────────────────


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def post_list(request):
    if request.method == "GET":
        qs = (
            Post.objects.filter(status=Post.Status.PUBLISHED)
            .select_related("author")
            .prefetch_related("tags")
            .order_by("-created_at")
        )
        return Response(paginate(qs, request, PostSerializer))

    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
        )

    title = (request.data.get("title") or "").strip()
    body = (request.data.get("body") or "").strip()
    excerpt = (request.data.get("excerpt") or "").strip()
    status_value = request.data.get("status", Post.Status.DRAFT)
    tag_ids = request.data.get("tag_ids") or []

    if not title or not body:
        return Response(
            {"detail": "title and body are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if status_value not in (Post.Status.DRAFT, Post.Status.PUBLISHED):
        return Response(
            {"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST
        )

    post = Post.objects.create(
        title=title,
        slug=build_unique_slug(Post, title),
        author=request.user,
        body=body,
        excerpt=excerpt,
        status=status_value,
        published_at=timezone.now() if status_value == Post.Status.PUBLISHED else None,
    )
    if tag_ids:
        tags = Tag.objects.filter(id__in=tag_ids)
        post.tags.set(tags)
    post.refresh_from_db()
    return Response(
        PostDetailSerializer(post, context={"request": request}).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def post_detail(request, slug):
    try:
        post = (
            Post.objects.select_related("author")
            .prefetch_related("tags", "comments__author", "comments__replies__author")
            .get(slug=slug)
        )
    except Post.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    role = getattr(getattr(request.user, "profile", None), "role", "user")

    if request.method == "GET":
        can_view_unpublished = request.user.is_authenticated and (
            post.author_id == request.user.id
            or request.user.is_superuser
            or request.user.is_staff
            or role in ("moderator", "admin")
        )
        if post.status != Post.Status.PUBLISHED and not can_view_unpublished:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(PostDetailSerializer(post, context={"request": request}).data)

    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED
        )

    can_manage_post = (
        post.author_id == request.user.id
        or request.user.is_superuser
        or request.user.is_staff
        or role in ("moderator", "admin")
    )
    if not can_manage_post:
        return Response(
            {"detail": "You can edit/delete only your own posts."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "DELETE":
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    title = request.data.get("title")
    body = request.data.get("body")
    excerpt = request.data.get("excerpt")
    status_value = request.data.get("status")
    tag_ids = request.data.get("tag_ids")

    if title is not None:
        title = title.strip()
        if not title:
            return Response(
                {"detail": "title cannot be empty."}, status=status.HTTP_400_BAD_REQUEST
            )
        post.title = title
        post.slug = build_unique_slug(Post, title, instance_id=post.id)
    if body is not None:
        body = body.strip()
        if not body:
            return Response(
                {"detail": "body cannot be empty."}, status=status.HTTP_400_BAD_REQUEST
            )
        post.body = body
    if excerpt is not None:
        post.excerpt = excerpt.strip()
    if status_value is not None:
        if status_value not in (Post.Status.DRAFT, Post.Status.PUBLISHED):
            return Response(
                {"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST
            )
        post.status = status_value
        post.published_at = (
            timezone.now() if status_value == Post.Status.PUBLISHED else None
        )

    post.save()
    if tag_ids is not None:
        tags = Tag.objects.filter(id__in=tag_ids)
        post.tags.set(tags)
    post.refresh_from_db()
    return Response(PostDetailSerializer(post, context={"request": request}).data)


# ── Tags ───────────────────────────────────────────────────────────────────────


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def tag_list(request):
    if request.method == "GET":
        qs = Tag.objects.order_by("name")
        return Response(paginate(qs, request, TagSerializer))

    if not can_manage_tags(request.user):
        return Response(
            {"detail": "Only moderators/admins can create tags."},
            status=status.HTTP_403_FORBIDDEN,
        )

    name = (request.data.get("name") or "").strip().lower()
    if not name:
        return Response(
            {"detail": "name is required."}, status=status.HTTP_400_BAD_REQUEST
        )
    if Tag.objects.filter(name=name).exists():
        return Response(
            {"detail": "Tag name already exists."}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        tag = Tag.objects.create(name=name, slug=build_unique_slug(Tag, name))
    except IntegrityError:
        return Response(
            {"detail": "Tag name already exists."}, status=status.HTTP_400_BAD_REQUEST
        )
    return Response(TagSerializer(tag).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def tag_detail(request, slug):
    try:
        tag = Tag.objects.get(slug=slug)
    except Tag.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        posts_qs = (
            Post.objects.filter(tags=tag, status=Post.Status.PUBLISHED)
            .select_related("author")
            .prefetch_related("tags")
            .order_by("-created_at")
        )
        return Response(
            {
                "tag": TagSerializer(tag).data,
                **paginate(posts_qs, request, PostSerializer),
            }
        )

    if not can_manage_tags(request.user):
        return Response(
            {"detail": "Only moderators/admins can manage tags."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "DELETE":
        tag.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    name = (request.data.get("name") or "").strip().lower()
    if not name:
        return Response(
            {"detail": "name is required."}, status=status.HTTP_400_BAD_REQUEST
        )
    if Tag.objects.filter(name=name).exclude(id=tag.id).exists():
        return Response(
            {"detail": "Tag name already exists."}, status=status.HTTP_400_BAD_REQUEST
        )

    tag.name = name
    tag.slug = build_unique_slug(Tag, name, instance_id=tag.id)
    tag.save()
    return Response(TagSerializer(tag).data)


# ── Users ──────────────────────────────────────────────────────────────────────


@api_view(["GET"])
@permission_classes([AllowAny])
def user_list(request):
    qs = User.objects.select_related("profile").order_by("-date_joined")
    return Response(paginate(qs, request, UserSerializer))


@api_view(["GET"])
@permission_classes([AllowAny])
def user_detail(request, username):
    try:
        user = User.objects.select_related("profile").get(username=username)
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    posts_qs = (
        Post.objects.filter(author=user, status=Post.Status.PUBLISHED)
        .prefetch_related("tags")
        .order_by("-created_at")
    )
    return Response(
        {
            "user": UserSerializer(user).data,
            **paginate(posts_qs, request, PostSerializer),
        }
    )


# ── Auth ───────────────────────────────────────────────────────────────────────


@api_view(["GET"])
@permission_classes([AllowAny])
def csrf(request):
    return Response({"csrfToken": get_token(request)})


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get("email", "")
    password = request.data.get("password", "")
    try:
        db_user = User.objects.get(email=email)
        username = db_user.username
    except (User.DoesNotExist, User.MultipleObjectsReturned):
        # Always run a dummy check to make response time indistinguishable from a
        # wrong-password attempt, preventing email enumeration via timing.
        check_password(password, _DUMMY_PASSWORD_HASH)
        return Response(
            {"detail": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST
        )
    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response(
            {"detail": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST
        )
    login(request, user)
    return Response(CurrentUserSerializer(user).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    email = request.data.get("email", "")
    username = request.data.get("username", "")
    password = request.data.get("password", "")
    if not email or not username or not password:
        return Response(
            {"detail": "email, username and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username, email=email, password=password
            )
    except IntegrityError:
        return Response(
            {"detail": "Registration failed."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    Profile.objects.get_or_create(user=user)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return Response(CurrentUserSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response({"detail": "Logged out."})


@api_view(["GET"])
def current_user(request):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Not authenticated."}, status=status.HTTP_401_UNAUTHORIZED
        )
    return Response(CurrentUserSerializer(request.user).data)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user
    new_username = request.data.get("username")
    current_password = request.data.get("current_password")
    new_password = request.data.get("new_password")

    errors = {}
    password_changed = False

    if new_username is not None:
        new_username = new_username.strip()
        if not new_username:
            errors["username"] = "Username cannot be empty."
        elif User.objects.filter(username=new_username).exclude(id=user.id).exists():
            errors["username"] = "Username already taken."
        else:
            user.username = new_username

    if new_password is not None:
        if not current_password:
            errors["current_password"] = (
                "Current password is required to change password."
            )
        elif not user.check_password(current_password):
            errors["current_password"] = "Current password is incorrect."
        else:
            new_password = new_password.strip()
            if len(new_password) < 8:
                errors["new_password"] = "Password must be at least 8 characters."
            else:
                user.set_password(new_password)
                password_changed = True

    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    user.save()
    if password_changed:
        update_session_auth_hash(request, user)

    return Response(CurrentUserSerializer(user).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def user_comments(request, username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    qs = (
        Comment.objects.filter(author=user)
        .select_related("post")
        .order_by("-created_at")
    )
    return Response(paginate(qs, request, CommentListSerializer))


# ── Comment Votes ──────────────────────────────────────────────────────────────


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def comment_vote(request, comment_id):
    vote_type = request.data.get("vote")
    if vote_type not in (CommentVote.VoteType.LIKE, CommentVote.VoteType.DISLIKE):
        return Response(
            {"detail": "vote must be 'like' or 'dislike'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    existing = CommentVote.objects.filter(comment=comment, user=request.user).first()
    if existing:
        if existing.vote == vote_type:
            existing.delete()  # toggle off
        else:
            existing.vote = vote_type
            existing.save()
    else:
        CommentVote.objects.create(comment=comment, user=request.user, vote=vote_type)

    comment.refresh_from_db()
    return Response(CommentSerializer(comment, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def comment_create(request, slug):
    body = (request.data.get("body") or "").strip()
    if not body:
        return Response(
            {"detail": "Comment body is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        post = Post.objects.get(slug=slug)
    except Post.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    parent_id = request.data.get("parent_id")
    parent = None
    if parent_id is not None:
        try:
            parent = Comment.objects.get(id=parent_id, post=post)
        except Comment.DoesNotExist:
            return Response(
                {"detail": "Parent comment not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    comment = Comment.objects.create(
        post=post,
        author=request.user,
        body=body,
        parent=parent,
        is_approved=True,
    )
    return Response(
        CommentSerializer(comment, context={"request": request}).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def comment_update(request, comment_id):
    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if comment.author_id != request.user.id:
        return Response(
            {"detail": "You can edit only your own comments."},
            status=status.HTTP_403_FORBIDDEN,
        )

    body = (request.data.get("body") or "").strip()
    if not body:
        return Response(
            {"detail": "Comment body is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    comment.body = body
    comment.save(update_fields=["body", "updated_at"])
    comment.refresh_from_db()
    return Response(CommentSerializer(comment, context={"request": request}).data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def comment_delete(request, comment_id):
    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if comment.author_id != request.user.id:
        return Response(
            {"detail": "You can delete only your own comments."},
            status=status.HTTP_403_FORBIDDEN,
        )

    comment.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
