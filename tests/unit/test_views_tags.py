"""Unit tests for tag API endpoints."""

import pytest
from django.contrib.auth.models import User
from rest_framework import status

from accounts.models import Profile
from blog.models import Post, Tag


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
        assert resp.data["name"] == "django"

    def test_admin_can_create_tag(self, admin_client):
        """An admin can create a new tag."""
        resp = admin_client.post("/api/tags/", {"name": "Flask"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED

    def test_regular_user_cannot_create_tag(self, auth_client):
        """A regular user is forbidden from creating tags."""
        resp = auth_client.post("/api/tags/", {"name": "Python"}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_create_tag(self, api_client):
        """An anonymous user is forbidden from creating tags."""
        resp = api_client.post("/api/tags/", {"name": "Django"}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_duplicate_tag_name_returns_400(self, mod_client, db):
        """Creating a tag with a name that already exists returns 400."""
        Tag.objects.create(name="django", slug="django")
        resp = mod_client.post("/api/tags/", {"name": "Django"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["detail"] == "Tag name already exists."

    def test_empty_name_returns_400(self, mod_client):
        """An empty tag name is rejected."""
        resp = mod_client.post("/api/tags/", {"name": ""}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_string_name_returns_400(self, mod_client):
        """Structured payloads are rejected cleanly."""
        resp = mod_client.post("/api/tags/", {"name": {"$ne": ""}}, format="json")
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

    def test_tag_detail_post_count_only_counts_published_posts(
        self, api_client, tag, user
    ):
        """Tag detail keeps published-only post_count semantics."""
        published_post = Post.objects.create(
            title="Published tagged",
            slug="published-tagged",
            author=user,
            body="body",
            status=Post.Status.PUBLISHED,
        )
        published_post.tags.add(tag)
        draft_post = Post.objects.create(
            title="Draft tagged",
            slug="draft-tagged",
            author=user,
            body="body",
            status=Post.Status.DRAFT,
        )
        draft_post.tags.add(tag)

        resp = api_client.get(f"/api/tags/{tag.slug}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["tag"]["post_count"] == 1

    def test_get_nonexistent_tag_returns_404(self, api_client):
        """A missing tag slug returns 404."""
        resp = api_client.get("/api/tags/no-such-tag/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_moderator_can_update_tag(self, mod_client, tag):
        """A moderator can rename a tag."""
        resp = mod_client.patch(
            f"/api/tags/{tag.slug}/", {"name": "updated python"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == "updated python"

    def test_regular_user_cannot_update_tag(self, auth_client, tag):
        """A regular user is forbidden from updating tags."""
        resp = auth_client.patch(
            f"/api/tags/{tag.slug}/", {"name": "Hack"}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_update_duplicate_name_returns_400(self, mod_client, tag, db):
        """Renaming a tag to an existing name is rejected."""
        Tag.objects.create(name="django", slug="django")
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


# ── Tag lowercase normalisation ────────────────────────────────────────────────


@pytest.mark.django_db
class TestTagLowercaseNormalisation:
    """Tags are always stored in lowercase regardless of input casing."""

    def test_uppercase_input_stored_as_lowercase_on_create(self, mod_client):
        """Uppercase name is normalised to lowercase when created."""
        resp = mod_client.post("/api/tags/", {"name": "FASTAPI"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["name"] == "fastapi"
        assert Tag.objects.filter(name="fastapi").exists()

    def test_mixed_case_input_stored_as_lowercase_on_create(self, mod_client):
        """Mixed-case name is normalised to lowercase when created."""
        resp = mod_client.post("/api/tags/", {"name": "CelEry"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["name"] == "celery"

    def test_already_lowercase_input_unchanged_on_create(self, mod_client):
        """Lowercase input passes through unchanged."""
        resp = mod_client.post("/api/tags/", {"name": "redis"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["name"] == "redis"

    def test_uppercase_input_stored_as_lowercase_on_update(self, mod_client, tag):
        """Uppercase name is normalised to lowercase on update."""
        resp = mod_client.patch(
            f"/api/tags/{tag.slug}/", {"name": "PYTHON"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == "python"

    def test_mixed_case_input_stored_as_lowercase_on_update(self, mod_client, tag):
        """Mixed-case name is normalised to lowercase on update."""
        resp = mod_client.patch(
            f"/api/tags/{tag.slug}/", {"name": "PyThOn TipS"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == "python tips"

    def test_duplicate_check_is_case_insensitive_on_create(self, mod_client, db):
        """Creating 'DJANGO' is rejected when 'django' already exists."""
        Tag.objects.create(name="django", slug="django")
        resp = mod_client.post("/api/tags/", {"name": "DJANGO"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["detail"] == "Tag name already exists."

    def test_duplicate_check_is_case_insensitive_on_update(self, mod_client, tag, db):
        """Renaming to 'DJANGO' is rejected when 'django' already exists."""
        Tag.objects.create(name="django", slug="django")
        resp = mod_client.patch(
            f"/api/tags/{tag.slug}/", {"name": "DJANGO"}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_whitespace_is_stripped_before_normalisation(self, mod_client):
        """Leading/trailing whitespace is stripped before lowercasing."""
        resp = mod_client.post("/api/tags/", {"name": "  Pytest  "}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["name"] == "pytest"


# ── can_manage_tags in user serializer ────────────────────────────────────────


@pytest.mark.django_db
class TestCanManageTagsSerializerField:
    """The can_manage_tags field on /api/auth/user/ reflects permission correctly."""

    def _get_user_data(self, client):
        resp = client.get("/api/auth/user/")
        assert resp.status_code == 200
        return resp.data

    def test_regular_user_cannot_manage_tags(self, auth_client):
        """Regular user has can_manage_tags=False."""
        data = self._get_user_data(auth_client)
        assert data["can_manage_tags"] is False

    def test_moderator_can_manage_tags(self, mod_client):
        """Moderator has can_manage_tags=True."""
        data = self._get_user_data(mod_client)
        assert data["can_manage_tags"] is True

    def test_admin_can_manage_tags(self, admin_client):
        """Admin has can_manage_tags=True."""
        data = self._get_user_data(admin_client)
        assert data["can_manage_tags"] is True

    def test_superuser_can_manage_tags(self, api_client, db):
        """Django superuser has can_manage_tags=True."""
        su = User.objects.create_superuser(
            username="super",
            email="super@example.com",
            password="pass",  # noqa: S106
        )
        Profile.objects.get_or_create(user=su)
        api_client.force_authenticate(user=su)
        data = self._get_user_data(api_client)
        assert data["can_manage_tags"] is True

    def test_staff_user_can_manage_tags(self, api_client, db):
        """Django staff user has can_manage_tags=True."""
        staff = User.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password="pass",  # noqa: S106
            is_staff=True,
        )
        Profile.objects.get_or_create(user=staff)
        api_client.force_authenticate(user=staff)
        data = self._get_user_data(api_client)
        assert data["can_manage_tags"] is True
