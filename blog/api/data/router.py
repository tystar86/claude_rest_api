"""
Unified data router — read + write operations on a single Router so that
Django Ninja merges overlapping paths (e.g. GET + POST on ``/posts/``) into
one PathView.  Separate read/write Routers caused 405s because Ninja creates
separate URL patterns per Router, and Django's resolver stops at the first
match.
"""

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import IntegrityError
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_protect
from ninja import Router

from blog import api_views
from blog.models import Comment, CommentVote, Post, Tag
from blog.serializers import (
    CommentListSerializer,
    CommentSerializer,
    PostDetailSerializer,
    PostSerializer,
    PostWriteSerializer,
    TagSerializer,
    UserSerializer,
)
from blog.utils import build_unique_slug

from ..auth.services import (
    AUTHENTICATION_REQUIRED_DETAIL,
    attach_forced_user,
    empty_compat_response,
    json_compat_response,
)
from ..throttling import READ_THROTTLES, WRITE_THROTTLES
from ..utils import request_data_or_error as _request_data_or_error
from .schemas import (
    DashboardResponse,
    NotFoundResponse,
    PaginatedCommentsResponse,
    PaginatedPostsResponse,
    PaginatedTagsResponse,
    PaginatedUsersResponse,
    PostDetailResponse,
    TagDetailResponse,
    UserDetailResponse,
)

router = Router(tags=["Data"], throttle=READ_THROTTLES)


def _serialize(serializer_class, obj, *, request=None, many=False):
    return serializer_class(obj, many=many, context={"request": request}).data


def _post_detail_queryset():
    return Post.objects.select_related("author").prefetch_related(
        "tags",
        "comments__author",
        "comments__votes",
        "comments__replies__author",
        "comments__replies__votes",
    )


# ── Dashboard ────────────────────────────────────────────────────────────────


@router.api_operation(["GET", "HEAD"], "/dashboard/", response=DashboardResponse)
def dashboard(request: HttpRequest):
    data = cache.get(api_views._DASHBOARD_CACHE_KEY)
    if data is None:
        data = api_views.build_dashboard_payload()
        cache.set(api_views._DASHBOARD_CACHE_KEY, data, api_views._DASHBOARD_CACHE_TTL)
    return json_compat_response(data)


# ── Posts ────────────────────────────────────────────────────────────────────


@router.api_operation(["GET", "HEAD"], "/posts/", response=PaginatedPostsResponse)
def post_list(request: HttpRequest):
    qs = api_views._published_posts_list_qs().order_by("-created_at")
    return json_compat_response(api_views.paginate(qs, request, PostSerializer))


@router.post("/posts/", throttle=WRITE_THROTTLES)
@csrf_protect
def create_post(request: HttpRequest):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response({"detail": "Authentication required."}, status=401)

    data, error = _request_data_or_error(request)
    if error is not None:
        return error
    serializer = PostWriteSerializer(data=data, context={"request": request})
    if not serializer.is_valid():
        return json_compat_response(dict(serializer.errors), status=400)

    post = serializer.save()
    post = _post_detail_queryset().get(pk=post.pk)
    payload = PostDetailSerializer(post, context={"request": request}).data
    return json_compat_response(payload, status=201)


@router.api_operation(
    ["GET", "HEAD"],
    "/posts/{slug}/",
    response={200: PostDetailResponse, 404: NotFoundResponse},
)
def post_detail(request: HttpRequest, slug: str):
    attach_forced_user(request)
    try:
        post = _post_detail_queryset().get(slug=slug)
    except Post.DoesNotExist:
        return empty_compat_response(status=404)

    if post.status != Post.Status.PUBLISHED and not api_views.can_view_unpublished_post(
        request.user, post
    ):
        return empty_compat_response(status=404)

    payload = _serialize(PostDetailSerializer, post, request=request)
    return json_compat_response(payload)


@router.patch("/posts/{slug}/", throttle=WRITE_THROTTLES)
@csrf_protect
def update_post(request: HttpRequest, slug: str):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response({"detail": "Authentication required."}, status=401)

    try:
        post = _post_detail_queryset().get(slug=slug)
    except Post.DoesNotExist:
        return empty_compat_response(status=404)

    if not api_views.can_view_unpublished_post(request.user, post):
        return json_compat_response(
            {"detail": "You can edit/delete only your own posts."}, status=403
        )

    data, error = _request_data_or_error(request)
    if error is not None:
        return error
    serializer = PostWriteSerializer(
        post, data=data, partial=True, context={"request": request}
    )
    if not serializer.is_valid():
        return json_compat_response(dict(serializer.errors), status=400)

    serializer.save()
    post = _post_detail_queryset().get(pk=post.pk)
    payload = PostDetailSerializer(post, context={"request": request}).data
    return json_compat_response(payload)


@router.delete("/posts/{slug}/", throttle=WRITE_THROTTLES)
@csrf_protect
def delete_post(request: HttpRequest, slug: str):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response({"detail": "Authentication required."}, status=401)

    try:
        post = _post_detail_queryset().get(slug=slug)
    except Post.DoesNotExist:
        return empty_compat_response(status=404)

    if not api_views.can_view_unpublished_post(request.user, post):
        return json_compat_response(
            {"detail": "You can edit/delete only your own posts."}, status=403
        )

    post.delete()
    return HttpResponse(status=204)


# ── Comments ─────────────────────────────────────────────────────────────────


@router.api_operation(["GET", "HEAD"], "/comments/", response=PaginatedCommentsResponse)
def comment_list(request: HttpRequest):
    qs = (
        Comment.objects.filter(post__status=Post.Status.PUBLISHED, is_approved=True)
        .select_related("author", "post")
        .prefetch_related("votes")
        .order_by("-created_at")
    )
    return json_compat_response(api_views.paginate(qs, request, CommentListSerializer))


@router.api_operation(
    ["GET", "HEAD"],
    "/posts/{slug}/comments/",
    response={200: PaginatedCommentsResponse, 404: NotFoundResponse},
)
def comment_list_by_post(request: HttpRequest, slug: str):
    attach_forced_user(request)
    try:
        post = Post.objects.select_related("author").get(slug=slug)
    except Post.DoesNotExist:
        return empty_compat_response(status=404)

    if post.status != Post.Status.PUBLISHED and not api_views.can_view_unpublished_post(
        request.user, post
    ):
        return empty_compat_response(status=404)

    qs = (
        Comment.objects.filter(post=post, is_approved=True)
        .select_related("author", "post")
        .prefetch_related("votes")
        .order_by("-created_at")
    )
    return json_compat_response(api_views.paginate(qs, request, CommentListSerializer))


@router.post("/posts/{slug}/comments/", throttle=WRITE_THROTTLES)
@csrf_protect
def comment_create(request: HttpRequest, slug: str):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response(
            {"detail": AUTHENTICATION_REQUIRED_DETAIL}, status=401
        )

    data, error = _request_data_or_error(request)
    if error is not None:
        return error
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
        return empty_compat_response(status=404)
    if post.status != Post.Status.PUBLISHED and not api_views.can_view_unpublished_post(
        request.user, post
    ):
        return empty_compat_response(status=404)

    parent_id = data.get("parent_id")
    parent = None
    if parent_id is not None:
        try:
            if isinstance(parent_id, bool):
                raise TypeError
            parent_id = int(parent_id)
        except (TypeError, ValueError):
            return json_compat_response({"detail": "Invalid parent_id."}, status=400)
        try:
            parent = Comment.objects.get(id=parent_id, post=post)
        except Comment.DoesNotExist:
            return json_compat_response(
                {"detail": "Parent comment not found."}, status=400
            )

    comment = Comment.objects.create(
        post=post, author=request.user, body=body, parent=parent, is_approved=True
    )
    payload = CommentSerializer(comment, context={"request": request}).data
    return json_compat_response(payload, status=201)


@router.post("/comments/{comment_id}/vote/", throttle=WRITE_THROTTLES)
@csrf_protect
def comment_vote(request: HttpRequest, comment_id: int):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response(
            {"detail": AUTHENTICATION_REQUIRED_DETAIL}, status=401
        )

    data, error = _request_data_or_error(request)
    if error is not None:
        return error
    vote_type = data.get("vote")
    if vote_type not in (CommentVote.VoteType.LIKE, CommentVote.VoteType.DISLIKE):
        return json_compat_response(
            {"detail": "vote must be 'like' or 'dislike'."}, status=400
        )

    try:
        comment = Comment.objects.select_related("post", "author").get(id=comment_id)
    except Comment.DoesNotExist:
        return empty_compat_response(status=404)
    if not api_views.can_access_comment(request.user, comment):
        return empty_compat_response(status=404)

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


@router.patch("/comments/{comment_id}/", throttle=WRITE_THROTTLES)
@csrf_protect
def comment_update(request: HttpRequest, comment_id: int):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response(
            {"detail": AUTHENTICATION_REQUIRED_DETAIL}, status=401
        )

    try:
        comment = Comment.objects.get(id=comment_id, author_id=request.user.id)
    except Comment.DoesNotExist:
        return empty_compat_response(status=404)

    data, error = _request_data_or_error(request)
    if error is not None:
        return error
    body = data.get("body")
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


@router.delete("/comments/{comment_id}/", throttle=WRITE_THROTTLES)
@csrf_protect
def comment_delete(request: HttpRequest, comment_id: int):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response(
            {"detail": AUTHENTICATION_REQUIRED_DETAIL}, status=401
        )

    try:
        comment = Comment.objects.get(id=comment_id, author_id=request.user.id)
    except Comment.DoesNotExist:
        return empty_compat_response(status=404)

    comment.delete()
    return HttpResponse(status=204)


# ── Tags ─────────────────────────────────────────────────────────────────────


@router.api_operation(["GET", "HEAD"], "/tags/", response=PaginatedTagsResponse)
def tag_list(request: HttpRequest):
    qs = Tag.objects.annotate(
        post_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
    ).order_by("name")
    return json_compat_response(api_views.paginate(qs, request, TagSerializer))


@router.post("/tags/", throttle=WRITE_THROTTLES)
@csrf_protect
def create_tag(request: HttpRequest):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response(
            {"detail": AUTHENTICATION_REQUIRED_DETAIL}, status=401
        )
    if not api_views.can_manage_tags(request.user):
        return json_compat_response(
            {"detail": "Only moderators/admins can create tags."}, status=403
        )

    data, error = _request_data_or_error(request)
    if error is not None:
        return error
    name = data.get("name")
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


@router.api_operation(
    ["GET", "HEAD"],
    "/tags/{slug}/",
    response={200: TagDetailResponse, 404: NotFoundResponse},
)
def tag_detail(request: HttpRequest, slug: str):
    try:
        tag = Tag.objects.annotate(
            post_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
        ).get(slug=slug)
    except Tag.DoesNotExist:
        return empty_compat_response(status=404)

    posts_qs = (
        Post.objects.filter(tags=tag, status=Post.Status.PUBLISHED)
        .select_related("author")
        .prefetch_related("tags")
        .order_by("-created_at")
    )
    payload = {
        "tag": _serialize(TagSerializer, tag, request=request),
        **api_views.paginate(posts_qs, request, PostSerializer),
    }
    return json_compat_response(payload)


@router.patch("/tags/{slug}/", throttle=WRITE_THROTTLES)
@csrf_protect
def update_tag(request: HttpRequest, slug: str):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response(
            {"detail": AUTHENTICATION_REQUIRED_DETAIL}, status=401
        )
    if not api_views.can_manage_tags(request.user):
        return json_compat_response(
            {"detail": "Only moderators/admins can manage tags."}, status=403
        )

    try:
        tag = Tag.objects.annotate(
            post_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
        ).get(slug=slug)
    except Tag.DoesNotExist:
        return empty_compat_response(status=404)

    data, error = _request_data_or_error(request)
    if error is not None:
        return error
    name = data.get("name")
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


@router.delete("/tags/{slug}/", throttle=WRITE_THROTTLES)
@csrf_protect
def delete_tag(request: HttpRequest, slug: str):
    attach_forced_user(request)
    if not request.user.is_authenticated:
        return json_compat_response(
            {"detail": AUTHENTICATION_REQUIRED_DETAIL}, status=401
        )
    if not api_views.can_manage_tags(request.user):
        return json_compat_response(
            {"detail": "Only moderators/admins can manage tags."}, status=403
        )

    try:
        tag = Tag.objects.annotate(
            post_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
        ).get(slug=slug)
    except Tag.DoesNotExist:
        return empty_compat_response(status=404)

    tag.delete()
    return HttpResponse(status=204)


# ── Users ────────────────────────────────────────────────────────────────────


@router.api_operation(["GET", "HEAD"], "/users/", response=PaginatedUsersResponse)
def user_list(request: HttpRequest):
    qs = (
        User.objects.select_related("profile")
        .annotate(
            post_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
        )
        .order_by("-date_joined")
    )
    return json_compat_response(api_views.paginate(qs, request, UserSerializer))


@router.api_operation(
    ["GET", "HEAD"],
    "/users/{username}/",
    response={200: UserDetailResponse, 404: NotFoundResponse},
)
def user_detail(request: HttpRequest, username: str):
    try:
        user = (
            User.objects.select_related("profile")
            .annotate(
                post_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
            )
            .get(username=username)
        )
    except User.DoesNotExist:
        return empty_compat_response(status=404)

    posts_qs = (
        Post.objects.filter(author=user, status=Post.Status.PUBLISHED)
        .prefetch_related("tags")
        .order_by("-created_at")
    )
    payload = {
        "user": _serialize(UserSerializer, user, request=request),
        **api_views.paginate(posts_qs, request, PostSerializer),
    }
    return json_compat_response(payload)


@router.api_operation(
    ["GET", "HEAD"],
    "/users/{username}/comments/",
    response={200: PaginatedCommentsResponse, 404: NotFoundResponse},
)
def user_comments(request: HttpRequest, username: str):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return empty_compat_response(status=404)

    qs = (
        Comment.objects.filter(
            author=user, post__status=Post.Status.PUBLISHED, is_approved=True
        )
        .select_related("author", "post")
        .prefetch_related("votes")
        .order_by("-created_at")
    )
    return json_compat_response(api_views.paginate(qs, request, CommentListSerializer))
