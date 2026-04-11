"""Preview tests for read-only Ninja migration routes."""

import json

import pytest
from rest_framework.test import APIClient
from rest_framework import status

from blog.models import Comment, Post


@pytest.mark.django_db
class TestNinjaReadPreview:
    """Smoke coverage for the preview read-only Ninja surface."""

    def test_openapi_json_is_available(self, api_client):
        resp = api_client.get("/api/_ninja/read/openapi.json")
        assert resp.status_code == status.HTTP_200_OK
        assert json.loads(resp.content)["openapi"] == "3.1.0"

    def test_dashboard_returns_expected_sections(self, api_client):
        resp = api_client.get("/api/_ninja/read/dashboard/")
        assert resp.status_code == status.HTTP_200_OK
        assert "stats" in resp.data
        assert "latest_posts" in resp.data
        assert "most_used_tags" in resp.data

    def test_post_list_is_paginated(self, api_client, post):
        resp = api_client.get("/api/_ninja/read/posts/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1
        assert "results" in resp.data

    def test_post_detail_honors_draft_visibility(self, api_client, user, draft_post):
        owner_client = APIClient()
        owner_client.force_authenticate(user=user)

        anon = api_client.get(f"/api/_ninja/read/posts/{draft_post.slug}/")
        owner = owner_client.get(f"/api/_ninja/read/posts/{draft_post.slug}/")

        assert anon.status_code == status.HTTP_404_NOT_FOUND
        assert owner.status_code == status.HTTP_200_OK
        assert owner.data["slug"] == draft_post.slug

    def test_comment_list_excludes_draft_post_comments(self, api_client, user):
        draft = Post.objects.create(
            title="Hidden Draft",
            slug="hidden-draft-preview",
            author=user,
            body="secret",
            status=Post.Status.DRAFT,
        )
        Comment.objects.create(
            post=draft,
            author=user,
            body="draft comment",
            is_approved=True,
        )
        published = Post.objects.create(
            title="Visible Post",
            slug="visible-post-preview",
            author=user,
            body="visible content",
            status=Post.Status.PUBLISHED,
        )
        Comment.objects.create(
            post=published,
            author=user,
            body="published comment",
            is_approved=True,
        )

        resp = api_client.get("/api/_ninja/read/comments/")
        assert resp.status_code == status.HTTP_200_OK
        slugs = [item["post_slug"] for item in resp.data["results"]]
        assert published.slug in slugs, "approved comment on published post must appear"
        assert draft.slug not in slugs, "comment on draft post must be excluded"

    def test_user_routes_are_available(self, api_client, post, comment):
        list_resp = api_client.get("/api/_ninja/read/users/")
        detail_resp = api_client.get(f"/api/_ninja/read/users/{post.author.username}/")
        comments_resp = api_client.get(
            f"/api/_ninja/read/users/{post.author.username}/comments/"
        )

        assert list_resp.status_code == status.HTTP_200_OK
        assert detail_resp.status_code == status.HTTP_200_OK
        assert comments_resp.status_code == status.HTTP_200_OK
        assert detail_resp.data["user"]["username"] == post.author.username
        assert all(
            item["author"] == str(post.author) for item in comments_resp.data["results"]
        )

    def test_missing_user_routes_return_404(self, api_client):
        detail_resp = api_client.get("/api/_ninja/read/users/no-such-user/")
        comments_resp = api_client.get("/api/_ninja/read/users/no-such-user/comments/")

        assert detail_resp.status_code == status.HTTP_404_NOT_FOUND
        assert comments_resp.status_code == status.HTTP_404_NOT_FOUND
