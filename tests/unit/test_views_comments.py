"""Unit tests for comment and vote API endpoints."""

import pytest
from django.contrib.auth import get_user_model

from blog.models import Comment, CommentVote, Post

User = get_user_model()


# ── Comment List ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCommentList:
    """Tests for GET /api/comments/."""

    def test_list_returns_200_for_anonymous(self, api_client, comment):
        """Anyone can list comments."""
        resp = api_client.get("/api/comments/")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_list_response_is_paginated(self, api_client):
        """Response includes pagination metadata."""
        data = api_client.get("/api/comments/").json()
        assert "count" in data
        assert "total_pages" in data
        assert "results" in data

    def test_list_includes_unapproved_on_published_posts(self, api_client, post, user):
        """Comments on published posts are listed regardless of is_approved."""
        Comment.objects.create(
            post=post,
            author=user,
            body="Awaiting moderation",
            is_approved=False,
        )
        resp = api_client.get("/api/comments/")
        assert resp.status_code == 200
        bodies = [item["body"] for item in resp.json()["results"]]
        assert "Awaiting moderation" in bodies

    def test_list_excludes_comments_on_draft_posts(self, api_client, user):
        """Anonymous users do not see comments attached to draft posts."""
        draft = Post.objects.create(
            title="Hidden Draft",
            slug="hidden-draft",
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

        resp = api_client.get("/api/comments/")
        assert resp.status_code == 200
        assert all(item["post_slug"] != "hidden-draft" for item in resp.json()["results"])

    def test_post_comments_list_returns_paginated_response(self, api_client, post, comment):
        """GET /api/posts/<slug>/comments/ returns paginated comments for the post."""
        resp = api_client.get(f"/api/posts/{post.slug}/comments/")
        data = resp.json()
        assert resp.status_code == 200
        assert "count" in data
        assert "total_pages" in data
        assert "results" in data
        assert all(item["post_slug"] == post.slug for item in data["results"])

    def test_post_comments_list_nonexistent_post_returns_404(self, api_client):
        """GET /api/posts/<slug>/comments/ returns 404 for missing posts."""
        resp = api_client.get("/api/posts/no-such-post/comments/")
        assert resp.status_code == 404


# ── Comment Create ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCommentCreate:
    """Tests for POST /api/posts/<slug>/comments/."""

    def test_authenticated_user_can_comment(self, auth_client, post):
        """An authenticated user can post a comment."""
        resp = auth_client.post(
            f"/api/posts/{post.slug}/comments/",
            {"body": "Great post!"},
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["body"] == "Great post!"

    def test_unauthenticated_user_cannot_comment(self, api_client, post):
        """An unauthenticated user is rejected."""
        resp = api_client.post(
            f"/api/posts/{post.slug}/comments/",
            {"body": "Hey"},
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_empty_body_returns_400(self, auth_client, post):
        """An empty comment body is rejected."""
        resp = auth_client.post(
            f"/api/posts/{post.slug}/comments/",
            {"body": ""},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_reply_to_existing_comment(self, auth_client, post, comment):
        """A reply links to the parent comment."""
        resp = auth_client.post(
            f"/api/posts/{post.slug}/comments/",
            {"body": "Reply!", "parent_id": comment.id},
            content_type="application/json",
        )
        assert resp.status_code == 201

    def test_nonexistent_post_returns_404(self, auth_client):
        """Commenting on a non-existent post returns 404."""
        resp = auth_client.post(
            "/api/posts/no-post/comments/",
            {"body": "body"},
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_invalid_parent_id_returns_400(self, auth_client, post):
        """A parent_id that doesn't exist on the post returns 400."""
        resp = auth_client.post(
            f"/api/posts/{post.slug}/comments/",
            {"body": "body", "parent_id": 99999},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_regular_user_cannot_comment_on_another_users_draft(self, api_client, draft_post):
        """A non-owner cannot comment on a draft post they cannot view."""
        other = User.objects.create_user(
            username="other-draft-user",
            email="other-draft@example.com",
            password="strongpass123",
        )
        api_client.force_login(other)
        resp = api_client.post(
            f"/api/posts/{draft_post.slug}/comments/",
            {"body": "Sneaky"},
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_non_string_body_returns_400(self, auth_client, post):
        """Structured JSON payloads are rejected cleanly."""
        resp = auth_client.post(
            f"/api/posts/{post.slug}/comments/",
            {"body": {"$ne": ""}},
            content_type="application/json",
        )
        assert resp.status_code == 400


# ── Comment Update ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCommentUpdate:
    """Tests for PATCH /api/comments/<id>/."""

    def test_author_can_update_own_comment(self, auth_client, comment):
        """A comment author can edit the body."""
        resp = auth_client.patch(
            f"/api/comments/{comment.id}/",
            {"body": "Edited body"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["body"] == "Edited body"

    def test_other_user_cannot_update_comment(self, api_client, comment, db):
        """A different user cannot edit someone else's comment."""
        other = User.objects.create_user(username="other", email="o@x.com", password="p")
        api_client.force_login(other)
        resp = api_client.patch(
            f"/api/comments/{comment.id}/",
            {"body": "Hacked"},
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_empty_body_returns_400(self, auth_client, comment):
        """Setting comment body to empty is rejected."""
        resp = auth_client.patch(
            f"/api/comments/{comment.id}/",
            {"body": ""},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_nonexistent_comment_returns_404(self, auth_client):
        """Updating a non-existent comment returns 404."""
        resp = auth_client.patch(
            "/api/comments/99999/",
            {"body": "body"},
            content_type="application/json",
        )
        assert resp.status_code == 404


# ── Comment Delete ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCommentDelete:
    """Tests for DELETE /api/comments/<id>/."""

    def test_author_can_delete_own_comment(self, auth_client, comment):
        """A comment author can delete their comment."""
        resp = auth_client.delete(f"/api/comments/{comment.id}/")
        assert resp.status_code == 204
        assert not Comment.objects.filter(id=comment.id).exists()

    def test_other_user_cannot_delete_comment(self, api_client, comment, db):
        """A different user cannot delete someone else's comment."""
        other = User.objects.create_user(username="other2", email="o2@x.com", password="p")
        api_client.force_login(other)
        resp = api_client.delete(f"/api/comments/{comment.id}/")
        assert resp.status_code == 404

    def test_nonexistent_comment_returns_404(self, auth_client):
        """Deleting a non-existent comment returns 404."""
        resp = auth_client.delete("/api/comments/99999/")
        assert resp.status_code == 404


# ── Comment Vote ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCommentVote:
    """Tests for POST /api/comments/<id>/vote/."""

    def test_like_comment(self, auth_client, comment):
        """Liking a comment increments the likes count."""
        resp = auth_client.post(
            f"/api/comments/{comment.id}/vote/",
            {"vote": "like"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["likes"] == 1

    def test_dislike_comment(self, auth_client, comment):
        """Disliking a comment increments the dislikes count."""
        resp = auth_client.post(
            f"/api/comments/{comment.id}/vote/",
            {"vote": "dislike"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["dislikes"] == 1

    def test_voting_same_type_twice_toggles_off(self, auth_client, user, comment):
        """Sending the same vote twice removes the vote (toggle off)."""
        CommentVote.objects.create(comment=comment, user=user, vote=CommentVote.VoteType.LIKE)
        resp = auth_client.post(
            f"/api/comments/{comment.id}/vote/",
            {"vote": "like"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["likes"] == 0

    def test_switching_vote_updates_counts(self, auth_client, user, comment):
        """Switching from like to dislike updates both counts correctly."""
        CommentVote.objects.create(comment=comment, user=user, vote=CommentVote.VoteType.LIKE)
        resp = auth_client.post(
            f"/api/comments/{comment.id}/vote/",
            {"vote": "dislike"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["likes"] == 0
        assert resp.json()["dislikes"] == 1

    def test_invalid_vote_type_returns_400(self, auth_client, comment):
        """An unrecognised vote type is rejected."""
        resp = auth_client.post(
            f"/api/comments/{comment.id}/vote/",
            {"vote": "invalid"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_unauthenticated_vote_returns_401(self, api_client, comment):
        """Unauthenticated users cannot vote."""
        resp = api_client.post(
            f"/api/comments/{comment.id}/vote/",
            {"vote": "like"},
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_vote_on_nonexistent_comment_returns_404(self, auth_client):
        """Voting on a non-existent comment returns 404."""
        resp = auth_client.post(
            "/api/comments/99999/vote/",
            {"vote": "like"},
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_vote_on_comment_for_hidden_draft_returns_404(self, api_client, draft_post):
        """Users cannot interact with comments tied to hidden draft posts."""
        owner = draft_post.author
        comment = Comment.objects.create(
            post=draft_post,
            author=owner,
            body="hidden comment",
            is_approved=True,
        )
        other = User.objects.create_user(
            username="vote-user",
            email="vote-user@example.com",
            password="strongpass123",
        )
        api_client.force_login(other)
        resp = api_client.post(
            f"/api/comments/{comment.id}/vote/",
            {"vote": "like"},
            content_type="application/json",
        )
        assert resp.status_code == 404
