import logging
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model


from django.db import connection
from django.db.models import Count, Q
from django.utils import timezone

from .models import Comment, CommentVote, Post, Tag
from .serializers import (
    PostSerializer,
    TagSerializer,
    UserSerializer,
)

User = get_user_model()

security_log = logging.getLogger("security")

PAGE_SIZE = 50
_MAX_PAGE = 10_000
# Dummy hash used for constant-time password check when user does not exist (prevents timing attacks).
_DUMMY_PASSWORD_HASH = make_password("_dummy_")


def paginate(qs, request, serializer_class, *, total_count: int | None = None):
    try:
        page = max(1, min(int(request.GET.get("page", 1)), _MAX_PAGE))
    except ValueError:
        page = 1
    total = total_count if total_count is not None else qs.count()
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


def can_manage_tags(user: User) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    role = getattr(user, "role", "user")
    return role in ("moderator", "admin")


def has_elevated_post_access(user: User, post: Post) -> bool:
    """True if the user may view unpublished content or modify a post (author/staff/mod)."""
    if not user.is_authenticated:
        return False
    role = getattr(user, "role", "user")
    return (
        post.author_id == user.id
        or user.is_superuser
        or user.is_staff
        or role in ("moderator", "admin")
    )


def can_access_comment(user: User, comment: Comment) -> bool:
    if comment.post.status == Post.Status.PUBLISHED:
        return True
    if not user.is_authenticated:
        return False
    if comment.author_id == user.id:
        return True
    return has_elevated_post_access(user, comment.post)


# ── Dashboard ──────────────────────────────────────────────────────────────────


def build_activity_payload() -> dict:
    """Recent public activity for the navbar ticker (no caching); used by /api/activity/."""
    # Single SQL round-trip replaces three ORM queries; ordering matches prior Coalesce(post) logic.
    post_table = Post._meta.db_table
    comment_table = Comment._meta.db_table
    user_table = User._meta.db_table
    status = Post.Status.PUBLISHED

    sql = f"""
        WITH
        lp AS (
            SELECT title, published_at, created_at
            FROM {post_table}
            WHERE status = %s
            ORDER BY COALESCE(published_at, created_at) DESC
            LIMIT 1
        ),
        lc AS (
            SELECT c.id, c.created_at, c.author_id, c.post_id
            FROM {comment_table} c
            INNER JOIN {post_table} p ON c.post_id = p.id
            WHERE p.status = %s
            ORDER BY c.created_at DESC
            LIMIT 1
        ),
        lu AS (
            SELECT username, date_joined
            FROM {user_table}
            ORDER BY date_joined DESC
            LIMIT 1
        )
        SELECT
            (SELECT title FROM lp),
            (SELECT COALESCE(published_at, created_at) FROM lp),
            (SELECT u.username FROM lc INNER JOIN {user_table} u ON u.id = lc.author_id),
            (SELECT created_at FROM lc),
            (SELECT p.title FROM lc INNER JOIN {post_table} p ON p.id = lc.post_id),
            (SELECT username FROM lu),
            (SELECT date_joined FROM lu)
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [status, status])
        row = cursor.fetchone()

    (
        latest_post_title,
        latest_post_at,
        latest_comment_author,
        latest_comment_at,
        latest_comment_post_title,
        latest_user_username,
        latest_user_joined_at,
    ) = row

    return {
        "latest_post_title": latest_post_title,
        "latest_post_at": latest_post_at,
        "latest_comment_author": latest_comment_author,
        "latest_comment_at": latest_comment_at,
        "latest_comment_post_title": latest_comment_post_title,
        "latest_user_username": latest_user_username,
        "latest_user_joined_at": latest_user_joined_at,
    }


def build_dashboard_payload():
    """Assemble dashboard JSON (no caching); used by Ninja read routes."""
    published = Post.published.all()
    published_ids = published.values("id")
    total_posts_count = published.count()
    total_comments_count = Comment.objects.filter(post__in=published_ids).count()
    total_authors_count = User.objects.filter(posts__in=published_ids).distinct().count()
    active_tags_count = Tag.objects.filter(posts__in=published_ids).distinct().count()
    cutoff_7d = timezone.now() - timedelta(days=7)
    new_posts_7d_count = published.filter(
        Q(published_at__gte=cutoff_7d)
        | (Q(published_at__isnull=True) & Q(created_at__gte=cutoff_7d))
    ).count()

    return {
        "stats": {
            "total_posts": total_posts_count,
            "comments": total_comments_count,
            "authors": total_authors_count,
            "active_tags": active_tags_count,
            "new_posts_7d": new_posts_7d_count,
        },
        "latest_posts": PostSerializer(
            Post.published.list_qs()[:10],
            many=True,
        ).data,
        "most_commented_posts": PostSerializer(
            Post.published.list_qs().order_by("-comment_count")[:10],
            many=True,
        ).data,
        "most_liked_posts": PostSerializer(
            Post.published.list_qs()
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
            Tag.objects.annotate(post_count=Count("posts", filter=Q(posts__in=published_ids)))
            .filter(post_count__gt=0)
            .order_by("-post_count")[:10],
            many=True,
        ).data,
        "top_authors": UserSerializer(
            User.objects.annotate(post_count=Count("posts", filter=Q(posts__in=published_ids)))
            .filter(post_count__gt=0)
            .order_by("-post_count")[:10],
            many=True,
        ).data,
    }


# Keep this module focused on shared query helpers and permission predicates for Ninja routes.
