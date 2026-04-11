from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Avg, Count, Q
from django.db.models.functions import Length
from django.http import HttpRequest
from ninja import Router

from blog import api_views
from blog.models import Comment, Post, Tag
from blog.serializers import (
    CommentListSerializer,
    PostDetailSerializer,
    PostSerializer,
    TagSerializer,
    UserSerializer,
)

from ..auth.services import (
    attach_forced_user,
    empty_compat_response,
    json_compat_response,
)
from .schemas import (
    DashboardResponse,
    PaginatedCommentsResponse,
    PaginatedPostsResponse,
    PaginatedTagsResponse,
    PaginatedUsersResponse,
    PostDetailResponse,
    TagDetailResponse,
    UserDetailResponse,
)


router = Router(tags=["Read API"])


def _serialize(
    serializer_class,
    obj,
    *,
    request: HttpRequest | None = None,
    many: bool = False,
):
    context = {"request": request} if request is not None else None
    serializer = serializer_class(obj, many=many, context=context)
    return serializer.data


@router.get("/dashboard/", response=DashboardResponse)
def dashboard(request: HttpRequest):
    data = cache.get(api_views._DASHBOARD_CACHE_KEY)
    if data is None:
        published = Post.objects.filter(status=Post.Status.PUBLISHED)
        total_posts = published.count()
        total_comments = Comment.objects.filter(
            post__status=Post.Status.PUBLISHED
        ).count()
        total_authors = (
            User.objects.filter(posts__status=Post.Status.PUBLISHED).distinct().count()
        )
        active_tags = (
            Tag.objects.filter(posts__status=Post.Status.PUBLISHED).distinct().count()
        )
        avg_chars = published.aggregate(avg=Avg(Length("body")))["avg"] or 0
        average_depth_words = round(avg_chars / 5)
        data = {
            "stats": {
                "total_posts": total_posts,
                "comments": total_comments,
                "authors": total_authors,
                "active_tags": active_tags,
                "average_depth_words": average_depth_words,
            },
            "latest_posts": _serialize(
                PostSerializer,
                api_views._published_posts_list_qs().order_by("-created_at")[:10],
                many=True,
            ),
            "most_commented_posts": _serialize(
                PostSerializer,
                api_views._published_posts_list_qs().order_by("-comment_count")[:10],
                many=True,
            ),
            "most_used_tags": _serialize(
                TagSerializer,
                Tag.objects.annotate(
                    post_count=Count(
                        "posts", filter=Q(posts__status=Post.Status.PUBLISHED)
                    )
                ).order_by("-post_count")[:10],
                many=True,
            ),
            "top_authors": _serialize(
                UserSerializer,
                User.objects.select_related("profile")
                .annotate(
                    post_count=Count(
                        "posts", filter=Q(posts__status=Post.Status.PUBLISHED)
                    )
                )
                .filter(post_count__gt=0)
                .order_by("-post_count")[:10],
                many=True,
            ),
        }
        cache.set(api_views._DASHBOARD_CACHE_KEY, data, api_views._DASHBOARD_CACHE_TTL)
    return json_compat_response(data)


@router.get("/comments/", response=PaginatedCommentsResponse)
def comment_list(request: HttpRequest):
    qs = (
        Comment.objects.filter(post__status=Post.Status.PUBLISHED, is_approved=True)
        .select_related("author", "post")
        .prefetch_related("votes")
        .order_by("-created_at")
    )
    return json_compat_response(api_views.paginate(qs, request, CommentListSerializer))


@router.get("/posts/", response=PaginatedPostsResponse)
def post_list(request: HttpRequest):
    qs = api_views._published_posts_list_qs().order_by("-created_at")
    return json_compat_response(api_views.paginate(qs, request, PostSerializer))


@router.get("/posts/{slug}/", response={200: PostDetailResponse, 404: None})
def post_detail(request: HttpRequest, slug: str):
    attach_forced_user(request)
    try:
        post = (
            Post.objects.select_related("author")
            .prefetch_related(
                "tags",
                "comments__author",
                "comments__votes",
                "comments__replies__author",
                "comments__replies__votes",
            )
            .get(slug=slug)
        )
    except Post.DoesNotExist:
        return empty_compat_response(status=404)

    if post.status != Post.Status.PUBLISHED and not api_views.can_view_unpublished_post(
        request.user, post
    ):
        return empty_compat_response(status=404)

    payload = _serialize(PostDetailSerializer, post, request=request)
    return json_compat_response(payload)


@router.get("/tags/", response=PaginatedTagsResponse)
def tag_list(request: HttpRequest):
    qs = Tag.objects.annotate(
        post_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
    ).order_by("name")
    return json_compat_response(api_views.paginate(qs, request, TagSerializer))


@router.get("/tags/{slug}/", response={200: TagDetailResponse, 404: None})
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
        "tag": _serialize(TagSerializer, tag),
        **api_views.paginate(posts_qs, request, PostSerializer),
    }
    return json_compat_response(payload)


@router.get("/users/", response=PaginatedUsersResponse)
def user_list(request: HttpRequest):
    qs = (
        User.objects.select_related("profile")
        .annotate(
            post_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
        )
        .order_by("-date_joined")
    )
    return json_compat_response(api_views.paginate(qs, request, UserSerializer))


@router.get("/users/{username}/", response={200: UserDetailResponse, 404: None})
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
        "user": _serialize(UserSerializer, user),
        **api_views.paginate(posts_qs, request, PostSerializer),
    }
    return json_compat_response(payload)


@router.get(
    "/users/{username}/comments/", response={200: PaginatedCommentsResponse, 404: None}
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
