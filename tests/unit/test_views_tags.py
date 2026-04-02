"""Unit tests for tag API endpoints."""

import pytest
from rest_framework import status

from blog.models import Tag


# ── Tag List ───────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTagList:
    """Tests for GET/POST /api/tags/."""

    def test_list_tags_returns_200_for_anonymous(self, api_client, tag):
        """Anyone can list tags."""
        resp = api_client.get("/api/tags/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1

    def test_list_response_is_paginated(self, api_client):
        """Response contains pagination metadata."""
        resp = api_client.get("/api/tags/")
        assert "count" in resp.data
        assert "total_pages" in resp.data
        assert "results" in resp.data

    def test_moderator_can_create_tag(self, mod_client):
        """A moderator can create a new tag."""
        resp = mod_client.post("/api/tags/", {"name": "Django"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["name"] == "Django"

    def test_admin_can_create_tag(self, admin_client):
        """An admin can create a new tag."""
        resp = admin_client.post("/api/tags/", {"name": "Flask"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED

    def test_regular_user_cannot_create_tag(self, auth_client):
        """A regular user is forbidden from creating tags."""
        resp = auth_client.post("/api/tags/", {"name": "Django"}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_create_tag(self, api_client):
        """An anonymous user is forbidden from creating tags."""
        resp = api_client.post("/api/tags/", {"name": "Django"}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_duplicate_tag_name_returns_400(self, mod_client, tag):
        """Creating a tag with a name that already exists returns 400."""
        resp = mod_client.post("/api/tags/", {"name": "Python"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["detail"] == "Tag name already exists."

    def test_empty_name_returns_400(self, mod_client):
        """An empty tag name is rejected."""
        resp = mod_client.post("/api/tags/", {"name": ""}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_generates_slug(self, mod_client):
        """A created tag receives an auto-generated slug."""
        resp = mod_client.post(
            "/api/tags/", {"name": "Machine Learning"}, format="json"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["slug"] == "machine-learning"


# ── Tag Detail ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTagDetail:
    """Tests for GET/PATCH/DELETE /api/tags/<slug>/."""

    def test_get_tag_returns_200(self, api_client, tag):
        """Anyone can retrieve a tag by slug."""
        resp = api_client.get(f"/api/tags/{tag.slug}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["tag"]["slug"] == tag.slug

    def test_get_tag_includes_posts(self, api_client, tag):
        """Tag detail response includes a posts list."""
        resp = api_client.get(f"/api/tags/{tag.slug}/")
        assert "results" in resp.data

    def test_get_nonexistent_tag_returns_404(self, api_client):
        """A missing tag slug returns 404."""
        resp = api_client.get("/api/tags/no-such-tag/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_moderator_can_update_tag(self, mod_client, tag):
        """A moderator can rename a tag."""
        resp = mod_client.patch(
            f"/api/tags/{tag.slug}/", {"name": "Updated Python"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == "Updated Python"

    def test_regular_user_cannot_update_tag(self, auth_client, tag):
        """A regular user is forbidden from updating tags."""
        resp = auth_client.patch(
            f"/api/tags/{tag.slug}/", {"name": "Hack"}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_update_duplicate_name_returns_400(self, mod_client, tag, db):
        """Renaming a tag to an existing name is rejected."""
        Tag.objects.create(name="Django", slug="django")
        resp = mod_client.patch(
            f"/api/tags/{tag.slug}/", {"name": "Django"}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_moderator_can_delete_tag(self, mod_client, tag):
        """A moderator can delete a tag."""
        resp = mod_client.delete(f"/api/tags/{tag.slug}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Tag.objects.filter(slug=tag.slug).exists()

    def test_regular_user_cannot_delete_tag(self, auth_client, tag):
        """A regular user is forbidden from deleting tags."""
        resp = auth_client.delete(f"/api/tags/{tag.slug}/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
