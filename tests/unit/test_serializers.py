"""Unit tests for DRF serializers."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.db.models import Count
from rest_framework.test import APIRequestFactory

from blog.models import Tag
from blog.serializers import (
    CommentSerializer,
    PostDetailSerializer,
    PostSerializer,
    ProfileSerializer,
    TagSerializer,
    UserSerializer,
)


# ── ProfileSerializer ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProfileSerializer:
    """Tests for ProfileSerializer."""

    def test_exposes_role_and_bio(self, user):
        """Serialized profile exposes exactly role and bio fields."""
        data = ProfileSerializer(user.profile).data
        assert set(data.keys()) == {"role", "bio"}

    def test_default_role_is_user(self, user):
        """A freshly created profile serializes with role='user'."""
        assert ProfileSerializer(user.profile).data["role"] == "user"

    def test_moderator_role_serialized(self, moderator):
        """A moderator profile serializes with role='moderator'."""
        assert ProfileSerializer(moderator.profile).data["role"] == "moderator"

    def test_bio_defaults_to_empty_string(self, user):
        """bio field serializes to an empty string when not set."""
        assert ProfileSerializer(user.profile).data["bio"] == ""


# ── UserSerializer ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestUserSerializer:
    """Tests for UserSerializer."""

    def test_exposes_expected_fields(self, user):
        """Serialized user contains all expected top-level fields."""
        data = UserSerializer(user).data
        assert {
            "id",
            "username",
            "email",
            "date_joined",
            "profile",
            "post_count",
        }.issubset(data.keys())

    def test_post_count_is_zero_initially(self, user):
        """post_count is 0 for a user with no posts."""
        assert UserSerializer(user).data["post_count"] == 0

    def test_post_count_reflects_posts(self, user, post):
        """post_count increments when the user has posts."""
        assert UserSerializer(user).data["post_count"] == 1

    def test_nested_profile_present(self, user):
        """profile is a nested object containing role and bio."""
        profile_data = UserSerializer(user).data["profile"]
        assert "role" in profile_data
        assert "bio" in profile_data


# ── TagSerializer ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTagSerializer:
    """Tests for TagSerializer."""

    def test_exposes_expected_fields(self, tag):
        """Serialized tag contains id, name, slug, and post_count."""
        assert set(TagSerializer(tag).data.keys()) == {
            "id",
            "name",
            "slug",
            "post_count",
        }

    def test_post_count_zero_for_unused_tag(self, tag):
        """post_count is 0 for a tag not linked to any post."""
        assert TagSerializer(tag).data["post_count"] == 0

    def test_post_count_reflects_linked_posts(self, tag, post):
        """post_count increases when a post references the tag."""
        post.tags.add(tag)
        annotated = Tag.objects.annotate(post_count=Count("posts")).get(pk=tag.pk)
        assert TagSerializer(annotated).data["post_count"] == 1


# ── PostSerializer ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPostSerializer:
    """Tests for PostSerializer."""

    def test_exposes_expected_fields(self, post):
        """Serialized post contains all standard list-view fields."""
        data = PostSerializer(post).data
        expected = {
            "id",
            "title",
            "slug",
            "author",
            "excerpt",
            "status",
            "tags",
            "created_at",
            "published_at",
            "comment_count",
        }
        assert expected.issubset(data.keys())

    def test_author_is_string(self, post):
        """author field serializes as a username string (StringRelatedField)."""
        assert PostSerializer(post).data["author"] == "testuser"

    def test_tags_is_list(self, post):
        """tags serializes as a list."""
        assert isinstance(PostSerializer(post).data["tags"], list)


# ── PostDetailSerializer ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPostDetailSerializer:
    """Tests for PostDetailSerializer."""

    def test_includes_body_and_comments(self, post):
        """Detail serializer adds body and comments on top of list fields."""
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = AnonymousUser()
        data = PostDetailSerializer(post, context={"request": request}).data
        assert "body" in data
        assert "comments" in data

    def test_comments_is_list(self, post, comment):
        """comments serializes as a list of comment objects."""
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = AnonymousUser()
        data = PostDetailSerializer(post, context={"request": request}).data
        assert isinstance(data["comments"], list)
        assert len(data["comments"]) == 1


# ── CommentSerializer ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCommentSerializer:
    """Tests for CommentSerializer."""

    def test_exposes_expected_fields(self, comment):
        """Serialized comment contains all expected fields."""
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = AnonymousUser()
        data = CommentSerializer(comment, context={"request": request}).data
        assert {
            "id",
            "author",
            "body",
            "created_at",
            "likes",
            "dislikes",
            "user_vote",
            "replies",
        }.issubset(data.keys())

    def test_likes_and_dislikes_default_to_zero(self, comment):
        """A new comment has zero likes and dislikes."""
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = AnonymousUser()
        data = CommentSerializer(comment, context={"request": request}).data
        assert data["likes"] == 0
        assert data["dislikes"] == 0

    def test_user_vote_is_none_for_anonymous(self, comment):
        """user_vote is None when the request has no authenticated user."""
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = AnonymousUser()
        data = CommentSerializer(comment, context={"request": request}).data
        assert data["user_vote"] is None
