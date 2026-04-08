"""Unit tests for the dashboard API endpoint."""

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework import status

from blog.models import Comment, Post, Tag


@pytest.mark.django_db
class TestDashboardView:
    """Tests for GET /api/dashboard/."""

    @pytest.fixture(autouse=True)
    def use_locmem_cache(self, settings):
        settings.CACHES = {
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "dashboard-view-tests",
            }
        }
        cache.clear()

    def test_returns_200_for_anonymous(self, api_client):
        """Anyone can access the dashboard."""
        resp = api_client.get("/api/dashboard/")
        assert resp.status_code == status.HTTP_200_OK

    def test_response_contains_top_level_keys(self, api_client):
        """Response includes all expected top-level sections."""
        resp = api_client.get("/api/dashboard/")
        assert "stats" in resp.data
        assert "latest_posts" in resp.data
        assert "most_commented_posts" in resp.data
        assert "most_used_tags" in resp.data
        assert "top_authors" in resp.data

    def test_stats_contains_expected_fields(self, api_client):
        """stats section exposes all expected counters."""
        resp = api_client.get("/api/dashboard/")
        stats = resp.data["stats"]
        assert "total_posts" in stats
        assert "comments" in stats
        assert "authors" in stats
        assert "active_tags" in stats
        assert "average_depth_words" not in stats

    def test_stats_reflect_created_content(self, api_client, post, comment):
        """Stats accurately count existing posts and comments."""
        resp = api_client.get("/api/dashboard/")
        stats = resp.data["stats"]
        assert stats["total_posts"] >= 1
        assert stats["comments"] >= 1

    def test_empty_database_returns_zero_stats(self, api_client, db):
        """All counters are 0 on an empty database."""
        resp = api_client.get("/api/dashboard/")
        stats = resp.data["stats"]
        assert stats["total_posts"] == 0
        assert stats["comments"] == 0
        assert stats["authors"] == 0
        assert stats["active_tags"] == 0

    def test_latest_posts_is_list(self, api_client):
        """latest_posts is always a list."""
        resp = api_client.get("/api/dashboard/")
        assert isinstance(resp.data["latest_posts"], list)

    def test_top_authors_only_includes_authors_with_posts(self, api_client, post):
        """top_authors only lists users who have at least one post."""
        resp = api_client.get("/api/dashboard/")
        for author in resp.data["top_authors"]:
            assert author["post_count"] > 0

    def test_post_create_invalidates_cached_snapshot(self, api_client, user, post):
        """A new published post invalidates the cached dashboard snapshot."""
        resp = api_client.get("/api/dashboard/")
        assert resp.data["stats"]["total_posts"] == 1

        Post.objects.create(
            title="Another published post",
            slug="another-published-post",
            author=user,
            body="New post body.",
            status=Post.Status.PUBLISHED,
        )

        resp = api_client.get("/api/dashboard/")
        assert resp.data["stats"]["total_posts"] == 2

    def test_comment_create_invalidates_cached_snapshot(
        self, api_client, post, comment, user
    ):
        """A new comment on a published post invalidates the cached dashboard snapshot."""
        resp = api_client.get("/api/dashboard/")
        assert resp.data["stats"]["comments"] == 1

        Comment.objects.create(
            post=post,
            author=user,
            body="Another comment.",
            is_approved=True,
        )

        resp = api_client.get("/api/dashboard/")
        assert resp.data["stats"]["comments"] == 2

    def test_draft_post_comments_excluded_from_comment_count(self, api_client, db):
        """Comments on draft posts are not counted in the stats comment total."""
        author = User.objects.create_user(
            username="draftauthor", email="draftauthor@x.com", password="p"
        )
        draft = Post.objects.create(
            title="Draft Only",
            slug="draft-only",
            author=author,
            body="Draft body.",
            status=Post.Status.DRAFT,
        )
        Comment.objects.create(
            post=draft,
            author=author,
            body="Comment on draft.",
            is_approved=True,
        )
        resp = api_client.get("/api/dashboard/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["stats"]["comments"] == 0

    def test_most_used_tags_excludes_draft_posts(self, api_client, db):
        """Tags attached only to draft posts appear with a post_count of 0 or are absent."""
        author = User.objects.create_user(
            username="tagdraftauthor", email="tagdraftauthor@x.com", password="p"
        )
        tag = Tag.objects.create(name="DraftTag", slug="draft-tag")
        draft = Post.objects.create(
            title="Draft Tagged",
            slug="draft-tagged",
            author=author,
            body="Draft body.",
            status=Post.Status.DRAFT,
        )
        draft.tags.add(tag)
        resp = api_client.get("/api/dashboard/")
        assert resp.status_code == status.HTTP_200_OK
        tag_entries = [t for t in resp.data["most_used_tags"] if t["slug"] == tag.slug]
        assert not tag_entries or tag_entries[0]["post_count"] == 0

    def test_top_authors_excludes_draft_only_authors(self, api_client, db):
        """Users who only have draft posts do not appear in top_authors."""
        draft_author = User.objects.create_user(
            username="draftonlyauthor", email="draftonlyauthor@x.com", password="p"
        )
        Post.objects.create(
            title="Only Draft",
            slug="only-draft",
            author=draft_author,
            body="Draft body.",
            status=Post.Status.DRAFT,
        )
        resp = api_client.get("/api/dashboard/")
        assert resp.status_code == status.HTTP_200_OK
        author_usernames = [a["username"] for a in resp.data["top_authors"]]
        assert draft_author.username not in author_usernames

    def test_tag_assignment_invalidates_cached_snapshot(self, api_client, post, tag):
        """Tag m2m changes invalidate the cached dashboard snapshot."""
        resp = api_client.get("/api/dashboard/")
        assert resp.data["stats"]["active_tags"] == 0

        post.tags.add(tag)

        resp = api_client.get("/api/dashboard/")
        assert resp.data["stats"]["active_tags"] == 1
