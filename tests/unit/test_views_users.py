"""Unit tests for public user read endpoints."""

import pytest


@pytest.mark.django_db
class TestUserListView:
    """Tests for GET /api/users/."""

    def test_list_users_returns_200(self, api_client, user):
        resp = api_client.get("/api/users/")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_list_users_is_paginated(self, api_client):
        resp = api_client.get("/api/users/")
        data = resp.json()
        assert "count" in data
        assert "total_pages" in data
        assert "results" in data


@pytest.mark.django_db
class TestUserDetailView:
    """Tests for GET /api/users/<username>/."""

    def test_detail_returns_user_and_posts(self, api_client, post):
        resp = api_client.get(f"/api/users/{post.author.username}/")
        data = resp.json()
        assert resp.status_code == 200
        assert data["user"]["username"] == post.author.username
        assert "results" in data

    def test_detail_returns_404_for_missing_user(self, api_client):
        resp = api_client.get("/api/users/no-such-user/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestUserCommentsView:
    """Tests for GET /api/users/<username>/comments/."""

    def test_comments_returns_paginated_results(self, api_client, comment):
        resp = api_client.get(f"/api/users/{comment.author.username}/comments/")
        data = resp.json()
        assert resp.status_code == 200
        assert "results" in data
        assert len(data["results"]) > 0, "fixture comment must appear in results"
        assert all(item["author"] == str(comment.author) for item in data["results"])

    def test_comments_returns_404_for_missing_user(self, api_client):
        resp = api_client.get("/api/users/no-such-user/comments/")
        assert resp.status_code == 404
