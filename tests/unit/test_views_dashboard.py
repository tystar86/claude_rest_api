"""Unit tests for the dashboard API endpoint."""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestDashboardView:
    """Tests for GET /api/dashboard/."""

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
        assert "average_depth_words" in stats

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
        assert stats["average_depth_words"] == 0

    def test_latest_posts_is_list(self, api_client):
        """latest_posts is always a list."""
        resp = api_client.get("/api/dashboard/")
        assert isinstance(resp.data["latest_posts"], list)

    def test_top_authors_only_includes_authors_with_posts(self, api_client, post):
        """top_authors only lists users who have at least one post."""
        resp = api_client.get("/api/dashboard/")
        for author in resp.data["top_authors"]:
            assert author["post_count"] > 0

    def test_average_depth_words_computed(self, api_client, post):
        """average_depth_words is a positive integer when posts exist."""
        resp = api_client.get("/api/dashboard/")
        assert resp.data["stats"]["average_depth_words"] > 0
