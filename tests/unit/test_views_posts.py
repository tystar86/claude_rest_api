"""Unit tests for post API endpoints."""

import pytest
from django.contrib.auth import get_user_model

from blog.models import Post

User = get_user_model()


# ── Post List ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPostList:
    """Tests for GET/POST /api/posts/."""

    def test_list_posts_returns_200_for_anonymous(self, api_client, post):
        """Anyone can list posts."""
        resp = api_client.get("/api/posts/")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_list_response_is_paginated(self, api_client, post):
        """Response contains pagination metadata."""
        resp = api_client.get("/api/posts/")
        data = resp.json()
        assert "count" in data
        assert "total_pages" in data
        assert "results" in data

    def test_create_post_authenticated_returns_201(self, auth_client):
        """An authenticated user can create a post."""
        resp = auth_client.post(
            "/api/posts/",
            {"title": "New Post", "body": "Some body text."},
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["title"] == "New Post"

    def test_create_post_unauthenticated_returns_401(self, api_client):
        """Unauthenticated users cannot create posts."""
        resp = api_client.post(
            "/api/posts/",
            {"title": "Fail", "body": "Fail"},
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_create_post_missing_title_returns_400(self, auth_client):
        """A post without a title is rejected."""
        resp = auth_client.post(
            "/api/posts/", {"body": "body only"}, content_type="application/json"
        )
        assert resp.status_code == 400

    def test_create_post_missing_body_returns_400(self, auth_client):
        """A post without a body is rejected."""
        resp = auth_client.post(
            "/api/posts/", {"title": "title only"}, content_type="application/json"
        )
        assert resp.status_code == 400

    def test_create_post_invalid_status_returns_400(self, auth_client):
        """An unrecognised status value is rejected."""
        resp = auth_client.post(
            "/api/posts/",
            {"title": "Bad Status", "body": "body", "status": "invalid"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_create_post_rejects_non_string_fields(self, auth_client):
        """Structured payloads for title/body do not crash the endpoint."""
        resp = auth_client.post(
            "/api/posts/",
            {"title": {"$ne": ""}, "body": "body"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_create_post_with_tags(self, auth_client, tag):
        """Tags are attached when tag_ids are provided."""
        resp = auth_client.post(
            "/api/posts/",
            {"title": "Tagged Post", "body": "body", "tag_ids": [tag.id]},
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert any(t["slug"] == tag.slug for t in resp.json()["tags"])

    def test_create_post_with_nonexistent_tag_ids_returns_400(self, auth_client):
        """Nonexistent tag IDs are rejected with a 400 response."""
        resp = auth_client.post(
            "/api/posts/",
            {"title": "Bad Tags", "body": "body", "tag_ids": [99999]},
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "tag_ids" in resp.json()

    def test_create_published_post_sets_published_at(self, auth_client):
        """Creating a published post populates published_at."""
        resp = auth_client.post(
            "/api/posts/",
            {"title": "Live Post", "body": "body", "status": "published"},
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["published_at"] is not None

    def test_create_draft_post_leaves_published_at_null(self, auth_client):
        """Creating a draft post leaves published_at as null."""
        resp = auth_client.post(
            "/api/posts/",
            {"title": "Draft Post", "body": "body", "status": "draft"},
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["published_at"] is None


# ── Post Detail ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPostDetail:
    """Tests for GET/PATCH/DELETE /api/posts/<slug>/."""

    def test_get_existing_post_returns_200(self, api_client, post):
        """Anyone can retrieve a post by slug."""
        resp = api_client.get(f"/api/posts/{post.slug}/")
        assert resp.status_code == 200
        assert resp.json()["slug"] == post.slug

    def test_get_nonexistent_post_returns_404(self, api_client):
        """A missing slug returns 404."""
        resp = api_client.get("/api/posts/no-such-post/")
        assert resp.status_code == 404

    def test_get_post_includes_comments(self, api_client, post, comment):
        """Detail response includes a comments list."""
        resp = api_client.get(f"/api/posts/{post.slug}/")
        assert "comments" in resp.json()

    def test_update_own_post_returns_200(self, auth_client, post):
        """An author can update their own post."""
        resp = auth_client.patch(
            f"/api/posts/{post.slug}/",
            {"title": "Updated Title"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    def test_update_other_user_post_returns_403(self, api_client, post, db):
        """A user cannot edit another user's post."""
        other = User.objects.create_user(username="other", email="other@x.com", password="p")
        api_client.force_login(other)
        resp = api_client.patch(
            f"/api/posts/{post.slug}/",
            {"title": "Hacked"},
            content_type="application/json",
        )
        assert resp.status_code == 403

    def test_moderator_can_update_any_post(self, mod_client, post):
        """Moderators can edit any post regardless of authorship."""
        resp = mod_client.patch(
            f"/api/posts/{post.slug}/",
            {"title": "Mod Edited"},
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_update_unauthenticated_returns_401(self, api_client, post):
        """Unauthenticated PATCH requests are rejected."""
        resp = api_client.patch(
            f"/api/posts/{post.slug}/",
            {"title": "Anon"},
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_update_unauthenticated_nonexistent_slug_still_returns_401(self, api_client):
        """Auth checks happen before slug lookup to avoid existence leaks."""
        resp = api_client.patch(
            "/api/posts/no-such-post/",
            {"title": "Anon"},
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_update_empty_title_returns_400(self, auth_client, post):
        """Setting title to an empty string is rejected."""
        resp = auth_client.patch(
            f"/api/posts/{post.slug}/",
            {"title": ""},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_update_empty_body_returns_400(self, auth_client, post):
        """Setting body to an empty string is rejected."""
        resp = auth_client.patch(
            f"/api/posts/{post.slug}/",
            {"body": ""},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_update_malformed_json_returns_400(self, auth_client, post):
        """Malformed JSON is rejected instead of being treated as an empty PATCH."""
        resp = auth_client.generic(
            "PATCH",
            f"/api/posts/{post.slug}/",
            "{not-json",
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Malformed JSON body."

    def test_update_rejects_non_string_title(self, auth_client, post):
        """Structured payloads do not crash post updates."""
        resp = auth_client.patch(
            f"/api/posts/{post.slug}/",
            {"title": {"$ne": ""}},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_delete_own_post_returns_204(self, auth_client, post):
        """An author can delete their own post."""
        resp = auth_client.delete(f"/api/posts/{post.slug}/")
        assert resp.status_code == 204
        assert not Post.objects.filter(slug=post.slug).exists()

    def test_delete_unauthenticated_returns_401(self, api_client, post):
        """Unauthenticated DELETE requests are rejected."""
        resp = api_client.delete(f"/api/posts/{post.slug}/")
        assert resp.status_code == 401

    def test_delete_unauthenticated_nonexistent_slug_still_returns_401(self, api_client):
        """Delete checks auth before slug lookup to reduce oracle surface."""
        resp = api_client.delete("/api/posts/no-such-post/")
        assert resp.status_code == 401

    def test_delete_other_user_post_returns_403(self, api_client, post, db):
        """A user cannot delete another user's post."""
        other = User.objects.create_user(username="other2", email="other2@x.com", password="p")
        api_client.force_login(other)
        resp = api_client.delete(f"/api/posts/{post.slug}/")
        assert resp.status_code == 403

    def test_get_draft_post_returns_404_for_anonymous(self, api_client, draft_post):
        """Anonymous users receive 404 when requesting a draft post."""
        resp = api_client.get(f"/api/posts/{draft_post.slug}/")
        assert resp.status_code == 404

    def test_get_draft_post_returns_200_for_author(self, auth_client, draft_post):
        """The post author can retrieve their own draft post."""
        resp = auth_client.get(f"/api/posts/{draft_post.slug}/")
        assert resp.status_code == 200
        assert resp.json()["slug"] == draft_post.slug

    def test_get_draft_post_returns_404_for_other_authenticated_user(
        self, api_client, draft_post, db
    ):
        """A different authenticated user receives 404 for another user's draft."""
        other = User.objects.create_user(username="other3", email="other3@x.com", password="p")
        api_client.force_login(other)
        resp = api_client.get(f"/api/posts/{draft_post.slug}/")
        assert resp.status_code == 404

    def test_get_draft_post_returns_200_for_moderator(self, mod_client, draft_post):
        """Moderators can view draft posts authored by other users."""
        resp = mod_client.get(f"/api/posts/{draft_post.slug}/")
        assert resp.status_code == 200
