"""Unit tests for public user read endpoints."""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestUserListView:
    """Tests for GET /api/users/."""

    def test_list_users_returns_200(self, api_client, user):
        resp = api_client.get("/api/users/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1

    def test_list_users_is_paginated(self, api_client):
        resp = api_client.get("/api/users/")
        assert "count" in resp.data
        assert "total_pages" in resp.data
        assert "results" in resp.data


@pytest.mark.django_db
class TestUserDetailView:
    """Tests for GET /api/users/<username>/."""

    def test_detail_returns_user_and_posts(self, api_client, post):
        resp = api_client.get(f"/api/users/{post.author.username}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["user"]["username"] == post.author.username
        assert "results" in resp.data

    def test_detail_returns_404_for_missing_user(self, api_client):
        resp = api_client.get("/api/users/no-such-user/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestUserCommentsView:
    """Tests for GET /api/users/<username>/comments/."""

    def test_comments_returns_paginated_results(self, api_client, comment):
        resp = api_client.get(f"/api/users/{comment.author.username}/comments/")
        assert resp.status_code == status.HTTP_200_OK
        assert "results" in resp.data
        assert all(
            item["author"] == str(comment.author) for item in resp.data["results"]
        )

    def test_comments_returns_404_for_missing_user(self, api_client):
        resp = api_client.get("/api/users/no-such-user/comments/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
