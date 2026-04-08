from __future__ import annotations

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Case, Count, IntegerField, Q, When

from .models import Comment, Post, Tag
from .serializers import PostSerializer, TagSerializer, UserSerializer

_DASHBOARD_CACHE_GENERATION_KEY = "dashboard_data_generation"
_DASHBOARD_CACHE_KEY_PREFIX = "dashboard_data"
_DASHBOARD_CACHE_TTL = 60 * 15
_DASHBOARD_REBUILD_LOCK_KEY = "dashboard_data_rebuild_lock"
_DASHBOARD_REBUILD_LOCK_TTL = 30
_DASHBOARD_LIMIT = 10


def _dashboard_generation() -> int:
    generation = cache.get(_DASHBOARD_CACHE_GENERATION_KEY)
    if generation is None:
        generation = 1
        cache.set(_DASHBOARD_CACHE_GENERATION_KEY, generation, None)
    return int(generation)


def _dashboard_cache_key(generation: int) -> str:
    return f"{_DASHBOARD_CACHE_KEY_PREFIX}:v{generation}"


def invalidate_dashboard_cache() -> None:
    generation = _dashboard_generation()
    try:
        cache.incr(_DASHBOARD_CACHE_GENERATION_KEY)
    except (AttributeError, NotImplementedError, ValueError):
        cache.set(_DASHBOARD_CACHE_GENERATION_KEY, generation + 1, None)


def _ordered_posts(post_ids: list[int]):
    if not post_ids:
        return Post.objects.none()

    order = Case(
        *[When(pk=post_id, then=position) for position, post_id in enumerate(post_ids)],
        output_field=IntegerField(),
    )
    return (
        Post.objects.filter(pk__in=post_ids)
        .defer("body")
        .select_related("author")
        .prefetch_related("tags")
        .annotate(comment_count=Count("comments", filter=Q(comments__is_approved=True)))
        .order_by(order)
    )


def _latest_post_ids() -> list[int]:
    return list(
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .order_by("-created_at")
        .values_list("id", flat=True)[:_DASHBOARD_LIMIT]
    )


def _most_commented_post_ids() -> list[int]:
    return list(
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .annotate(comment_count=Count("comments", filter=Q(comments__is_approved=True)))
        .order_by("-comment_count", "-created_at")
        .values_list("id", flat=True)[:_DASHBOARD_LIMIT]
    )


def build_dashboard_data() -> dict[str, object]:
    published = Post.objects.filter(status=Post.Status.PUBLISHED)
    active_tags = (
        Post.tags.through.objects.filter(post__status=Post.Status.PUBLISHED)
        .values("tag_id")
        .distinct()
        .count()
    )

    return {
        "stats": {
            "total_posts": published.count(),
            "comments": Comment.objects.filter(
                post__status=Post.Status.PUBLISHED
            ).count(),
            "authors": published.values("author_id").distinct().count(),
            "active_tags": active_tags,
        },
        "latest_posts": PostSerializer(
            _ordered_posts(_latest_post_ids()), many=True
        ).data,
        "most_commented_posts": PostSerializer(
            _ordered_posts(_most_commented_post_ids()),
            many=True,
        ).data,
        "most_used_tags": TagSerializer(
            Tag.objects.annotate(
                post_count=Count(
                    "posts",
                    filter=Q(posts__status=Post.Status.PUBLISHED),
                    distinct=True,
                )
            ).order_by("-post_count", "name")[:_DASHBOARD_LIMIT],
            many=True,
        ).data,
        "top_authors": UserSerializer(
            User.objects.select_related("profile")
            .annotate(
                post_count=Count(
                    "posts",
                    filter=Q(posts__status=Post.Status.PUBLISHED),
                    distinct=True,
                )
            )
            .filter(post_count__gt=0)
            .order_by("-post_count", "username")[:_DASHBOARD_LIMIT],
            many=True,
        ).data,
    }


def get_dashboard_data() -> dict[str, object]:
    generation = _dashboard_generation()
    cache_key = _dashboard_cache_key(generation)
    data = cache.get(cache_key)
    if data is not None:
        return data

    lock_acquired = cache.add(
        _DASHBOARD_REBUILD_LOCK_KEY,
        generation,
        _DASHBOARD_REBUILD_LOCK_TTL,
    )
    try:
        if not lock_acquired:
            data = cache.get(cache_key)
            if data is not None:
                return data

        data = build_dashboard_data()
        cache.set(cache_key, data, _DASHBOARD_CACHE_TTL)
        return data
    finally:
        if lock_acquired:
            cache.delete(_DASHBOARD_REBUILD_LOCK_KEY)
