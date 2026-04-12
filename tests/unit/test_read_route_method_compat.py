"""Regression tests for public read-route HTTP method compatibility."""

import pytest


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/api/dashboard/", "/api/comments/", "/api/users/"])
def test_public_read_list_routes_keep_options(api_client, path):
    """Read list routes still answer OPTIONS after the Ninja GET cutover."""
    resp = api_client.options(path)
    assert resp.status_code == 200
    allow = resp.headers.get("Allow", "")
    assert "GET" in allow
    assert "OPTIONS" in allow


@pytest.mark.django_db
def test_public_user_detail_route_keeps_options(api_client, user):
    """User detail route supports OPTIONS metadata requests."""
    resp = api_client.options(f"/api/users/{user.username}/")
    assert resp.status_code == 200
    allow = resp.headers.get("Allow", "")
    assert "GET" in allow
    assert "OPTIONS" in allow


@pytest.mark.django_db
def test_public_user_comments_route_keeps_options(api_client, user):
    """User comments route supports OPTIONS metadata requests."""
    resp = api_client.options(f"/api/users/{user.username}/comments/")
    assert resp.status_code == 200
    allow = resp.headers.get("Allow", "")
    assert "GET" in allow
    assert "OPTIONS" in allow
