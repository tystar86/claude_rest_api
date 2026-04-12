"""Unit tests for blog serializers."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.db.models import Count, IntegerField, Value
from django.test import RequestFactory

from blog.models import Post, Tag
from blog.serializers import (
    CommentSerializer,
    CurrentUserSerializer,
    PostDetailSerializer,
    PostSerializer,
    ProfileSerializer,
    TagSerializer,
    UserSerializer,
)
from blog.services import PostService


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
        data = CurrentUserSerializer(user).data
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

    def test_comment_count_integer_when_queryset_not_annotated(self, post, comment):
        """Without a comment_count annotation, count all related comments."""
        data = PostSerializer(post).data
        assert data["comment_count"] == 1
        assert isinstance(data["comment_count"], int)

    def test_comment_count_prefers_annotation_when_present(self, post, comment):
        """Annotated comment_count wins over a live DB count."""
        annotated = Post.objects.annotate(comment_count=Value(99, output_field=IntegerField())).get(
            pk=post.pk
        )
        assert PostSerializer(annotated).data["comment_count"] == 99


# ── PostDetailSerializer ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPostDetailSerializer:
    """Tests for PostDetailSerializer."""

    def test_includes_body_and_comments(self, post):
        """Detail serializer adds body and comments on top of list fields."""
        factory = RequestFactory()
        request = factory.get("/")
        request.user = AnonymousUser()
        data = PostDetailSerializer(post, context={"request": request}).data
        assert "body" in data
        assert "comments" in data

    def test_comments_is_list(self, post, comment):
        """comments serializes as a list of comment objects."""
        factory = RequestFactory()
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
        factory = RequestFactory()
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
        factory = RequestFactory()
        request = factory.get("/")
        request.user = AnonymousUser()
        data = CommentSerializer(comment, context={"request": request}).data
        assert data["likes"] == 0
        assert data["dislikes"] == 0

    def test_user_vote_is_none_for_anonymous(self, comment):
        """user_vote is None when the request has no authenticated user."""
        factory = RequestFactory()
        request = factory.get("/")
        request.user = AnonymousUser()
        data = CommentSerializer(comment, context={"request": request}).data
        assert data["user_vote"] is None


# ── PostService — tag_ids validation on create ─────────────────────────────────


@pytest.mark.django_db
class TestPostServiceTagValidation:
    """Tests for PostService.create tag_ids handling."""

    def test_valid_tag_ids_accepted(self, user, tag):
        """Existing tag IDs pass validation and are linked."""
        post, errors = PostService.create(
            author=user,
            data={"title": "T", "body": "B", "tag_ids": [tag.id]},
        )
        assert not errors, errors
        assert post is not None
        assert set(post.tags.values_list("id", flat=True)) == {tag.id}

    def test_nonexistent_tag_id_rejected(self, user):
        """A tag ID that doesn't exist causes a validation error."""
        post, errors = PostService.create(
            author=user,
            data={"title": "T", "body": "B", "tag_ids": [99999]},
        )
        assert post is None
        assert "tag_ids" in errors

    def test_mix_of_valid_and_invalid_tag_ids_rejected(self, user, tag):
        """If any tag ID is invalid, the whole field fails validation."""
        post, errors = PostService.create(
            author=user,
            data={"title": "T", "body": "B", "tag_ids": [tag.id, 99999]},
        )
        assert post is None
        assert "tag_ids" in errors

    def test_null_tag_ids_accepted(self, user):
        """null tag_ids is allowed (field has allow_null=True)."""
        post, errors = PostService.create(
            author=user,
            data={"title": "T", "body": "B", "tag_ids": None},
        )
        assert not errors, errors
        assert post is not None
        assert post.tags.count() == 0

    def test_omitted_tag_ids_accepted(self, user):
        """Omitting tag_ids entirely is valid (field is not required)."""
        post, errors = PostService.create(
            author=user,
            data={"title": "T", "body": "B"},
        )
        assert not errors, errors
        assert post is not None
        assert post.tags.count() == 0

    def test_empty_tag_ids_accepted(self, user):
        """An empty list is valid."""
        post, errors = PostService.create(
            author=user,
            data={"title": "T", "body": "B", "tag_ids": []},
        )
        assert not errors, errors
        assert post is not None
        assert post.tags.count() == 0

    def test_error_message_lists_missing_ids(self, user, tag):
        """The validation error message includes the specific missing IDs."""
        post, errors = PostService.create(
            author=user,
            data={"title": "T", "body": "B", "tag_ids": [tag.id, 77777, 88888]},
        )
        assert post is None
        error_msg = errors["tag_ids"][0]
        assert "77777" in str(error_msg)
        assert "88888" in str(error_msg)

    def test_bool_in_tag_ids_rejected(self, user, tag):
        """JSON booleans must not be accepted as integer tag IDs."""
        post, errors = PostService.create(
            author=user,
            data={"title": "T", "body": "B", "tag_ids": [True]},
        )
        assert post is None
        assert "tag_ids" in errors

    def test_null_status_rejected(self, user):
        """Explicit null status is invalid on create."""
        post, errors = PostService.create(
            author=user,
            data={"title": "T", "body": "B", "status": None},
        )
        assert post is None
        assert "status" in errors


# ── PostService — update ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPostServiceUpdate:
    """Tests for PostService.update."""

    def test_title_change_regenerates_slug(self, user, post):
        """Changing title rebuilds slug from the new title."""
        old_slug = post.slug
        _, errors = PostService.update(
            instance=post,
            data={"title": "Completely New Title Here"},
        )
        assert not errors, errors
        post.refresh_from_db()
        assert post.title == "Completely New Title Here"
        assert post.slug != old_slug
        assert post.slug.startswith("completely-new")

    def test_publish_sets_published_at(self, user, draft_post):
        """Setting status to published sets published_at when missing."""
        assert draft_post.published_at is None
        _, errors = PostService.update(
            instance=draft_post,
            data={"status": Post.Status.PUBLISHED},
        )
        assert not errors, errors
        draft_post.refresh_from_db()
        assert draft_post.status == Post.Status.PUBLISHED
        assert draft_post.published_at is not None

    def test_unpublish_clears_published_at(self, user, draft_post):
        """Reverting to draft clears published_at (Post has no unpublished_at field)."""
        assert draft_post.published_at is None
        _, err_pub = PostService.update(instance=draft_post, data={"status": Post.Status.PUBLISHED})
        assert not err_pub, err_pub
        draft_post.refresh_from_db()
        assert draft_post.published_at is not None
        _, err_draft = PostService.update(instance=draft_post, data={"status": Post.Status.DRAFT})
        assert not err_draft, err_draft
        draft_post.refresh_from_db()
        assert draft_post.status == Post.Status.DRAFT
        assert draft_post.published_at is None

    def test_null_status_rejected(self, user, post):
        _, errors = PostService.update(instance=post, data={"status": None})
        assert "status" in errors

    def test_valid_tag_ids_replace_tags(self, user, post, tag):
        t2 = Tag.objects.create(name="Rust", slug="rust")
        post.tags.add(tag)
        _, errors = PostService.update(instance=post, data={"tag_ids": [t2.id]})
        assert not errors, errors
        post.refresh_from_db()
        assert set(post.tags.values_list("id", flat=True)) == {t2.id}

    def test_mix_of_valid_and_invalid_tag_ids_rejected(self, user, post, tag):
        post.tags.add(tag)
        _, errors = PostService.update(
            instance=post,
            data={"tag_ids": [tag.id, 424242]},
        )
        assert "tag_ids" in errors
        assert "424242" in str(errors["tag_ids"][0])

    def test_null_tag_ids_leaves_tags_unchanged(self, user, post, tag):
        post.tags.add(tag)
        _, errors = PostService.update(instance=post, data={"tag_ids": None})
        assert not errors, errors
        post.refresh_from_db()
        assert set(post.tags.values_list("id", flat=True)) == {tag.id}

    def test_empty_tag_ids_clears_tags(self, user, post, tag):
        post.tags.add(tag)
        _, errors = PostService.update(instance=post, data={"tag_ids": []})
        assert not errors, errors
        post.refresh_from_db()
        assert post.tags.count() == 0

    def test_omitted_tag_ids_leaves_tags_unchanged(self, user, post, tag):
        post.tags.add(tag)
        _, errors = PostService.update(instance=post, data={"title": "Only title"})
        assert not errors, errors
        post.refresh_from_db()
        assert post.title == "Only title"
        assert set(post.tags.values_list("id", flat=True)) == {tag.id}
