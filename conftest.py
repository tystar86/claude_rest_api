"""Root pytest configuration and shared fixtures for the entire test suite."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from blog.models import Comment, Post, Tag

User = get_user_model()


# ── API clients ────────────────────────────────────────────────────────────────


@pytest.fixture
def api_client():
    """Unauthenticated Django test client."""
    return Client()


@pytest.fixture
def auth_client(api_client, user):
    """Django test client authenticated as a regular user."""
    api_client.force_login(user)
    return api_client


@pytest.fixture
def mod_client(api_client, moderator):
    """Django test client authenticated as a moderator."""
    api_client.force_login(moderator)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Django test client authenticated as an admin."""
    api_client.force_login(admin_user)
    return api_client


# ── Users ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    """Regular user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def moderator(db):
    """User with the moderator role."""
    return User.objects.create_user(
        username="moduser",
        email="mod@example.com",
        password="modpass123",
        role="moderator",
    )


@pytest.fixture
def admin_user(db):
    """User with the admin role."""
    return User.objects.create_user(
        username="adminuser",
        email="admin@example.com",
        password="adminpass123",
        role="admin",
    )


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
