"""Unit tests for GET /api/activity/ (header ticker payload)."""

import pytest


@pytest.mark.django_db
class TestActivityView:
    """Tests for GET /api/activity/."""

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

    def test_empty_database_nullable_fields(self, api_client, db):
        data = api_client.get("/api/activity/").json()
        assert data["latest_post_title"] is None
        assert data["latest_comment_at"] is None
        assert data["latest_user_username"] is None
