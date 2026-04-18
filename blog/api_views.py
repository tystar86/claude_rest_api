import logging
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User

from django.db.models import Avg, Count, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce, Length

from .models import Comment, CommentVote, Post, Tag
from .serializers import (
    PostSerializer,
    TagSerializer,
    UserSerializer,
)

security_log = logging.getLogger("security")

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
    items = serializer_class(
        qs[start : start + PAGE_SIZE],
        many=True,
        context={"request": request},
    ).data
    return {
        "count": total,
        "total_pages": max(1, -(-total // PAGE_SIZE)),
        "page": page,
        "results": items,
    }


def _published_posts_list_qs():
    """Queryset for PostSerializer list cards: skip heavy body, count comments on published posts."""
    comment_count_sq = (
        Comment.objects.filter(post=OuterRef("pk"))
        .order_by()
        .values("post")
        .annotate(cnt=Count("id"))
        .values("cnt")
    )
    return (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .defer("body")
        .select_related("author")
        .prefetch_related("tags")
        .annotate(
            comment_count=Coalesce(Subquery(comment_count_sq, output_field=IntegerField()), 0)
        )
    )


def can_manage_tags(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    role = getattr(getattr(user, "profile", None), "role", "user")
    return role in ("moderator", "admin")


def has_elevated_post_access(user, post):
    """True if the user may view unpublished content or modify a post (author/staff/mod)."""
    if not user.is_authenticated:
        return False
    role = getattr(getattr(user, "profile", None), "role", "user")
    return (
        post.author_id == user.id
        or user.is_superuser
        or user.is_staff
        or role in ("moderator", "admin")
    )


def can_access_comment(user, comment):
    if comment.post.status == Post.Status.PUBLISHED:
        return True
    if not user.is_authenticated:
        return False
    if comment.author_id == user.id:
        return True
    return has_elevated_post_access(user, comment.post)


# ── Dashboard ──────────────────────────────────────────────────────────────────


_DASHBOARD_CACHE_KEY = "dashboard_data"
_DASHBOARD_CACHE_TTL = 60  # seconds


def build_dashboard_payload():
    """Assemble dashboard JSON (no caching); used by Ninja read routes."""
    published = Post.objects.filter(status=Post.Status.PUBLISHED)
    total_posts = published.count()
    total_comments = Comment.objects.filter(post__status=Post.Status.PUBLISHED).count()
    total_authors = User.objects.filter(posts__status=Post.Status.PUBLISHED).distinct().count()
    active_tags = Tag.objects.filter(posts__status=Post.Status.PUBLISHED).distinct().count()

    avg_chars = published.aggregate(avg=Avg(Length("body")))["avg"] or 0
    average_depth_words = round(avg_chars / 5)

    latest_post = published.order_by("-published_at", "-created_at").defer("body").first()
    latest_comment = (
        Comment.objects.filter(post__status=Post.Status.PUBLISHED)
        .select_related("author", "post")
        .order_by("-created_at")
        .first()
    )
    latest_user = User.objects.order_by("-date_joined").first()

    activity = {
        "latest_post_title": None,
        "latest_post_at": None,
        "latest_comment_author": None,
        "latest_comment_at": None,
        "latest_comment_post_title": None,
        "latest_user_username": None,
        "latest_user_joined_at": None,
    }
    if latest_post:
        activity["latest_post_title"] = latest_post.title
        activity["latest_post_at"] = latest_post.published_at or latest_post.created_at
    if latest_comment:
        activity["latest_comment_author"] = latest_comment.author.username
        activity["latest_comment_at"] = latest_comment.created_at
        activity["latest_comment_post_title"] = latest_comment.post.title
    if latest_user:
        activity["latest_user_username"] = latest_user.username
        activity["latest_user_joined_at"] = latest_user.date_joined

    return {
        "stats": {
            "total_posts": total_posts,
            "comments": total_comments,
            "authors": total_authors,
            "active_tags": active_tags,
            "average_depth_words": average_depth_words,
        },
        "activity": activity,
        "latest_posts": PostSerializer(
            _published_posts_list_qs().order_by("-created_at")[:10],
            many=True,
        ).data,
        "most_commented_posts": PostSerializer(
            _published_posts_list_qs().order_by("-comment_count")[:10],
            many=True,
        ).data,
        "most_liked_posts": PostSerializer(
            _published_posts_list_qs()
            .annotate(
                comment_like_count=Count(
                    "comments__votes",
                    filter=Q(comments__votes__vote=CommentVote.VoteType.LIKE),
                )
            )
            .filter(comment_like_count__gt=0)
            .order_by("-comment_like_count", "-created_at")[:10],
            many=True,
        ).data,
        "most_used_tags": TagSerializer(
            Tag.objects.annotate(
                post_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
            )
            .filter(post_count__gt=0)
            .order_by("-post_count")[:10],
            many=True,
        ).data,
        "top_authors": UserSerializer(
            User.objects.select_related("profile")
            .annotate(post_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED)))
            .filter(post_count__gt=0)
            .order_by("-post_count")[:10],
            many=True,
        ).data,
    }


# Keep this module focused on shared query helpers and permission predicates for Ninja routes.
