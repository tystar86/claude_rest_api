"""Unit tests for post API endpoints."""

import pytest
from django.contrib.auth.models import User
from rest_framework import status

from blog.models import Post


# ── Post List ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPostList:
    """Tests for GET/POST /api/posts/."""

    def test_list_posts_returns_200_for_anonymous(self, api_client, post):
        """Anyone can list posts."""
        resp = api_client.get("/api/posts/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1

    def test_list_response_is_paginated(self, api_client, post):
        """Response contains pagination metadata."""
        resp = api_client.get("/api/posts/")
        assert "count" in resp.data
        assert "total_pages" in resp.data
        assert "results" in resp.data

    def test_create_post_authenticated_returns_201(self, auth_client):
        """An authenticated user can create a post."""
        resp = auth_client.post(
            "/api/posts/",
            {"title": "New Post", "body": "Some body text."},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["title"] == "New Post"

    def test_create_post_unauthenticated_returns_401(self, api_client):
        """Unauthenticated users cannot create posts."""
        resp = api_client.post(
            "/api/posts/", {"title": "Fail", "body": "Fail"}, format="json"
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_post_missing_title_returns_400(self, auth_client):
        """A post without a title is rejected."""
        resp = auth_client.post("/api/posts/", {"body": "body only"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_post_missing_body_returns_400(self, auth_client):
        """A post without a body is rejected."""
        resp = auth_client.post("/api/posts/", {"title": "title only"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_post_invalid_status_returns_400(self, auth_client):
        """An unrecognised status value is rejected."""
        resp = auth_client.post(
            "/api/posts/",
            {"title": "Bad Status", "body": "body", "status": "invalid"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_post_rejects_non_string_fields(self, auth_client):
        """Structured payloads for title/body do not crash the endpoint."""
        resp = auth_client.post(
            "/api/posts/",
            {"title": {"$ne": ""}, "body": "body"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_post_with_tags(self, auth_client, tag):
        """Tags are attached when tag_ids are provided."""
        resp = auth_client.post(
            "/api/posts/",
            {"title": "Tagged Post", "body": "body", "tag_ids": [tag.id]},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert any(t["slug"] == tag.slug for t in resp.data["tags"])

    def test_create_post_with_nonexistent_tag_ids_returns_400(self, auth_client):
        """Nonexistent tag IDs are rejected with a 400 response."""
        resp = auth_client.post(
            "/api/posts/",
            {"title": "Bad Tags", "body": "body", "tag_ids": [99999]},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "tag_ids" in resp.data

    def test_create_published_post_sets_published_at(self, auth_client):
        """Creating a published post populates published_at."""
        resp = auth_client.post(
            "/api/posts/",
            {"title": "Live Post", "body": "body", "status": "published"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["published_at"] is not None

    def test_create_draft_post_leaves_published_at_null(self, auth_client):
        """Creating a draft post leaves published_at as null."""
        resp = auth_client.post(
            "/api/posts/",
            {"title": "Draft Post", "body": "body", "status": "draft"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["published_at"] is None


# ── Post Detail ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPostDetail:
    """Tests for GET/PATCH/DELETE /api/posts/<slug>/."""

    def test_get_existing_post_returns_200(self, api_client, post):
        """Anyone can retrieve a post by slug."""
        resp = api_client.get(f"/api/posts/{post.slug}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["slug"] == post.slug

    def test_get_nonexistent_post_returns_404(self, api_client):
        """A missing slug returns 404."""
        resp = api_client.get("/api/posts/no-such-post/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_post_includes_comments(self, api_client, post, comment):
        """Detail response includes a comments list."""
        resp = api_client.get(f"/api/posts/{post.slug}/")
        assert "comments" in resp.data

    def test_update_own_post_returns_200(self, auth_client, post):
        """An author can update their own post."""
        resp = auth_client.patch(
            f"/api/posts/{post.slug}/", {"title": "Updated Title"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["title"] == "Updated Title"

    def test_update_other_user_post_returns_403(self, api_client, post, db):
        """A user cannot edit another user's post."""
        other = User.objects.create_user(
            username="other", email="other@x.com", password="p"
        )
        api_client.force_authenticate(user=other)
        resp = api_client.patch(
            f"/api/posts/{post.slug}/", {"title": "Hacked"}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_moderator_can_update_any_post(self, mod_client, post):
        """Moderators can edit any post regardless of authorship."""
        resp = mod_client.patch(
            f"/api/posts/{post.slug}/", {"title": "Mod Edited"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_update_unauthenticated_returns_401(self, api_client, post):
        """Unauthenticated PATCH requests are rejected."""
        resp = api_client.patch(
            f"/api/posts/{post.slug}/", {"title": "Anon"}, format="json"
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_empty_title_returns_400(self, auth_client, post):
        """Setting title to an empty string is rejected."""
        resp = auth_client.patch(
            f"/api/posts/{post.slug}/", {"title": ""}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_empty_body_returns_400(self, auth_client, post):
        """Setting body to an empty string is rejected."""
        resp = auth_client.patch(
            f"/api/posts/{post.slug}/", {"body": ""}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_rejects_non_string_title(self, auth_client, post):
        """Structured payloads do not crash post updates."""
        resp = auth_client.patch(
            f"/api/posts/{post.slug}/", {"title": {"$ne": ""}}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_own_post_returns_204(self, auth_client, post):
        """An author can delete their own post."""
        resp = auth_client.delete(f"/api/posts/{post.slug}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Post.objects.filter(slug=post.slug).exists()

    def test_delete_unauthenticated_returns_401(self, api_client, post):
        """Unauthenticated DELETE requests are rejected."""
        resp = api_client.delete(f"/api/posts/{post.slug}/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_other_user_post_returns_403(self, api_client, post, db):
        """A user cannot delete another user's post."""
        other = User.objects.create_user(
            username="other2", email="other2@x.com", password="p"
        )
        api_client.force_authenticate(user=other)
        resp = api_client.delete(f"/api/posts/{post.slug}/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_get_draft_post_returns_404_for_anonymous(self, api_client, draft_post):
        """Anonymous users receive 404 when requesting a draft post."""
        resp = api_client.get(f"/api/posts/{draft_post.slug}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_draft_post_returns_200_for_author(self, auth_client, draft_post):
        """The post author can retrieve their own draft post."""
        resp = auth_client.get(f"/api/posts/{draft_post.slug}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["slug"] == draft_post.slug

    def test_get_draft_post_returns_404_for_other_authenticated_user(
        self, api_client, draft_post, db
    ):
        """A different authenticated user receives 404 for another user's draft."""
        other = User.objects.create_user(
            username="other3", email="other3@x.com", password="p"
        )
        api_client.force_authenticate(user=other)
        resp = api_client.get(f"/api/posts/{draft_post.slug}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_draft_post_returns_200_for_moderator(self, mod_client, draft_post):
        """Moderators can view draft posts authored by other users."""
        resp = mod_client.get(f"/api/posts/{draft_post.slug}/")
        assert resp.status_code == status.HTTP_200_OK
