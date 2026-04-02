"""Root pytest configuration and shared fixtures for the entire test suite."""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from accounts.models import Profile
from blog.models import Comment, Post, Tag


# ── API clients ────────────────────────────────────────────────────────────────


@pytest.fixture
def api_client():
    """Unauthenticated DRF test client."""
    return APIClient()


@pytest.fixture
def auth_client(api_client, user):
    """DRF test client authenticated as a regular user."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def mod_client(api_client, moderator):
    """DRF test client authenticated as a moderator."""
    api_client.force_authenticate(user=moderator)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """DRF test client authenticated as an admin."""
    api_client.force_authenticate(user=admin_user)
    return api_client


# ── Users ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    """Regular user with an associated Profile."""
    u = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )
    Profile.objects.get_or_create(user=u)
    return u


@pytest.fixture
def moderator(db):
    """User with the moderator role.

    Uses a bulk UPDATE + re-fetch to bypass the Django ORM cache that
    accounts/signals.py places on the user instance at creation time.
    """
    u = User.objects.create_user(
        username="moduser",
        email="mod@example.com",
        password="modpass123",
    )
    Profile.objects.filter(user=u).update(role=Profile.Role.MODERATOR)
    return User.objects.select_related("profile").get(pk=u.pk)


@pytest.fixture
def admin_user(db):
    """User with the admin role.

    Uses a bulk UPDATE + re-fetch to bypass the Django ORM cache that
    accounts/signals.py places on the user instance at creation time.
    """
    u = User.objects.create_user(
        username="adminuser",
        email="admin@example.com",
        password="adminpass123",
    )
    Profile.objects.filter(user=u).update(role=Profile.Role.ADMIN)
    return User.objects.select_related("profile").get(pk=u.pk)


# ── Content ────────────────────────────────────────────────────────────────────


@pytest.fixture
def tag(db):
    """A single Tag instance."""
    return Tag.objects.create(name="Python", slug="python")


@pytest.fixture
def post(db, user):
    """A published Post authored by the regular user."""
    return Post.objects.create(
        title="Test Post",
        slug="test-post",
        author=user,
        body="This is the body of the test post.",
        status=Post.Status.PUBLISHED,
    )


@pytest.fixture
def draft_post(db, user):
    """A draft Post authored by the regular user."""
    return Post.objects.create(
        title="Draft Post",
        slug="draft-post",
        author=user,
        body="This is a draft post body.",
        status=Post.Status.DRAFT,
    )


@pytest.fixture
def comment(db, post, user):
    """An approved top-level Comment on the test post."""
    return Comment.objects.create(
        post=post,
        author=user,
        body="Test comment body.",
        is_approved=True,
    )
