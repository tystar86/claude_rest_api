"""Unit tests for blog and accounts models."""

import pytest
from django.db import IntegrityError

from accounts.models import Profile
from blog.models import Comment, CommentVote, Post, Tag


# ── Tag ────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTagModel:
    """Tests for the Tag model."""

    def test_str_returns_name(self):
        """__str__ returns the tag name."""
        tag = Tag(name="Python", slug="python")
        assert str(tag) == "Python"

    def test_slug_must_be_unique(self, db):
        """Two tags cannot share the same slug."""
        Tag.objects.create(name="Python", slug="python")
        with pytest.raises(IntegrityError):
            Tag.objects.create(name="Python Duplicate", slug="python")

    def test_name_must_be_unique(self, db):
        """Two tags cannot share the same name."""
        Tag.objects.create(name="Python", slug="python")
        with pytest.raises(IntegrityError):
            Tag.objects.create(name="Python", slug="python-2")


# ── Post ───────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPostModel:
    """Tests for the Post model."""

    def test_str_returns_title(self, post):
        """__str__ returns the post title."""
        assert str(post) == "Test Post"

    def test_default_status_is_draft(self, user):
        """A post created without explicit status defaults to draft."""
        p = Post.objects.create(title="Draft", slug="draft-x", author=user, body="body")
        assert p.status == Post.Status.DRAFT

    def test_published_status_is_set(self, post):
        """The fixture post has published status."""
        assert post.status == Post.Status.PUBLISHED

    def test_tags_many_to_many(self, post, tag):
        """Tags can be added to and retrieved from a post."""
        post.tags.add(tag)
        assert tag in post.tags.all()

    def test_slug_must_be_unique(self, user):
        """Two posts cannot share the same slug."""
        Post.objects.create(title="P1", slug="same-slug", author=user, body="a")
        with pytest.raises(IntegrityError):
            Post.objects.create(title="P2", slug="same-slug", author=user, body="b")

    def test_excerpt_defaults_to_blank(self, user):
        """excerpt is optional and defaults to an empty string."""
        p = Post.objects.create(title="T", slug="t-slug", author=user, body="body")
        assert p.excerpt == ""

    def test_published_at_is_nullable(self, user):
        """A draft post has a null published_at."""
        p = Post.objects.create(title="T", slug="t2", author=user, body="body")
        assert p.published_at is None


# ── Comment ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCommentModel:
    """Tests for the Comment model."""

    def test_str_contains_author_and_post(self, comment, user, post):
        """__str__ mentions both the author and the post title."""
        result = str(comment)
        assert user.username in result
        assert post.title in result

    def test_default_is_not_approved(self, post, user):
        """A freshly created comment is unapproved by default."""
        c = Comment.objects.create(post=post, author=user, body="Unapproved")
        assert not c.is_approved

    def test_threaded_reply(self, post, user, comment):
        """A reply links back to its parent and appears in parent.replies."""
        reply = Comment.objects.create(
            post=post, author=user, body="Reply", parent=comment, is_approved=True
        )
        assert reply.parent == comment
        assert reply in comment.replies.all()

    def test_top_level_comment_has_no_parent(self, comment):
        """A top-level comment has parent=None."""
        assert comment.parent is None


# ── CommentVote ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCommentVoteModel:
    """Tests for the CommentVote model."""

    def test_str_contains_username_and_vote(self, comment, user):
        """__str__ contains the voter's name and vote type."""
        vote = CommentVote.objects.create(
            comment=comment, user=user, vote=CommentVote.VoteType.LIKE
        )
        assert user.username in str(vote)
        assert "like" in str(vote)

    def test_unique_constraint_prevents_duplicate_vote(self, comment, user):
        """A user cannot cast two votes on the same comment."""
        CommentVote.objects.create(
            comment=comment, user=user, vote=CommentVote.VoteType.LIKE
        )
        with pytest.raises(IntegrityError):
            CommentVote.objects.create(
                comment=comment, user=user, vote=CommentVote.VoteType.DISLIKE
            )

    def test_like_and_dislike_choices(self):
        """VoteType exposes LIKE and DISLIKE as expected values."""
        assert CommentVote.VoteType.LIKE == "like"
        assert CommentVote.VoteType.DISLIKE == "dislike"


# ── Profile ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProfileModel:
    """Tests for the accounts Profile model."""

    def test_default_role_is_user(self, user):
        """A newly created profile defaults to the 'user' role."""
        assert user.profile.role == Profile.Role.USER

    def test_moderator_role(self, moderator):
        """is_moderator returns True for users with the moderator role."""
        assert moderator.profile.is_moderator

    def test_admin_role(self, admin_user):
        """is_admin returns True for users with the admin role."""
        assert admin_user.profile.is_admin

    def test_admin_is_also_moderator(self, admin_user):
        """Admins pass the is_moderator check as well."""
        assert admin_user.profile.is_moderator

    def test_regular_user_is_not_moderator(self, user):
        """Regular users do not pass the is_moderator check."""
        assert not user.profile.is_moderator

    def test_str_contains_username(self, user):
        """__str__ includes the username."""
        assert user.username in str(user.profile)

    def test_bio_defaults_to_blank(self, user):
        """bio field defaults to an empty string."""
        assert user.profile.bio == ""
