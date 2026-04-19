"""Unit tests for GET /api/activity/ (header ticker payload)."""

from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone

from blog import api_views
from blog.models import Post


@pytest.mark.django_db
class TestActivityView:
    """Tests for GET /api/activity/."""

    @pytest.fixture(autouse=True)
    def _clear_activity_cache(self):
        cache.delete(api_views._ACTIVITY_CACHE_KEY)
        yield

    def test_returns_200_for_anonymous(self, api_client):
        resp = api_client.get("/api/activity/")
        assert resp.status_code == 200

    def test_head_returns_200(self, api_client):
        resp = api_client.head("/api/activity/")
        assert resp.status_code == 200

    def test_response_is_ticker_fields_only(self, api_client):
        data = api_client.get("/api/activity/").json()
        assert set(data.keys()) == {
            "latest_post_title",
            "latest_post_at",
            "latest_comment_author",
            "latest_comment_at",
            "latest_comment_post_title",
            "latest_user_username",
            "latest_user_joined_at",
        }

    def test_reflects_post_and_comment(self, api_client, post, comment):
        data = api_client.get("/api/activity/").json()
        assert data["latest_post_title"] == post.title
        assert data["latest_comment_author"] == comment.author.username

    def test_empty_database_nullable_fields(self, api_client):
        data = api_client.get("/api/activity/").json()
        assert data["latest_post_title"] is None
        assert data["latest_comment_at"] is None
        assert data["latest_user_username"] is None

    def test_latest_post_orders_by_effective_publish_time(self, api_client, user):
        """NULL published_at must not outrank a newer real publication via NULLS FIRST."""
        now = timezone.now()
        Post.objects.create(
            title="Older explicit publish",
            slug="older-explicit",
            author=user,
            body="a",
            status=Post.Status.PUBLISHED,
            published_at=now - timedelta(days=2),
        )
        null_pub = Post.objects.create(
            title="Null publish newer created",
            slug="null-pub-newer-created",
            author=user,
            body="b",
            status=Post.Status.PUBLISHED,
            published_at=None,
        )
        Post.objects.filter(pk=null_pub.pk).update(created_at=now - timedelta(days=10))
        data = api_client.get("/api/activity/").json()
        assert data["latest_post_title"] == "Older explicit publish"
