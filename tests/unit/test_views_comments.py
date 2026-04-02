"""Unit tests for comment and vote API endpoints."""

import pytest
from django.contrib.auth.models import User
from rest_framework import status

from blog.models import Comment, CommentVote


# ── Comment List ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCommentList:
    """Tests for GET /api/comments/."""

    def test_list_returns_200_for_anonymous(self, api_client, comment):
        """Anyone can list comments."""
        resp = api_client.get("/api/comments/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1

    def test_list_response_is_paginated(self, api_client):
        """Response includes pagination metadata."""
        resp = api_client.get("/api/comments/")
        assert "count" in resp.data
        assert "total_pages" in resp.data
        assert "results" in resp.data


# ── Comment Create ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCommentCreate:
    """Tests for POST /api/posts/<slug>/comments/."""

    def test_authenticated_user_can_comment(self, auth_client, post):
        """An authenticated user can post a comment."""
        resp = auth_client.post(
            f"/api/posts/{post.slug}/comments/",
            {"body": "Great post!"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["body"] == "Great post!"

    def test_unauthenticated_user_cannot_comment(self, api_client, post):
        """An unauthenticated user is rejected."""
        resp = api_client.post(
            f"/api/posts/{post.slug}/comments/",
            {"body": "Hey"},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_empty_body_returns_400(self, auth_client, post):
        """An empty comment body is rejected."""
        resp = auth_client.post(
            f"/api/posts/{post.slug}/comments/",
            {"body": ""},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_reply_to_existing_comment(self, auth_client, post, comment):
        """A reply links to the parent comment."""
        resp = auth_client.post(
            f"/api/posts/{post.slug}/comments/",
            {"body": "Reply!", "parent_id": comment.id},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_nonexistent_post_returns_404(self, auth_client):
        """Commenting on a non-existent post returns 404."""
        resp = auth_client.post(
            "/api/posts/no-post/comments/",
            {"body": "body"},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_parent_id_returns_400(self, auth_client, post):
        """A parent_id that doesn't exist on the post returns 400."""
        resp = auth_client.post(
            f"/api/posts/{post.slug}/comments/",
            {"body": "body", "parent_id": 99999},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ── Comment Update ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCommentUpdate:
    """Tests for PATCH /api/comments/<id>/."""

    def test_author_can_update_own_comment(self, auth_client, comment):
        """A comment author can edit the body."""
        resp = auth_client.patch(
            f"/api/comments/{comment.id}/",
            {"body": "Edited body"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["body"] == "Edited body"

    def test_other_user_cannot_update_comment(self, api_client, comment, db):
        """A different user cannot edit someone else's comment."""
        other = User.objects.create_user(
            username="other", email="o@x.com", password="p"
        )
        api_client.force_authenticate(user=other)
        resp = api_client.patch(
            f"/api/comments/{comment.id}/", {"body": "Hacked"}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_empty_body_returns_400(self, auth_client, comment):
        """Setting comment body to empty is rejected."""
        resp = auth_client.patch(
            f"/api/comments/{comment.id}/", {"body": ""}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_nonexistent_comment_returns_404(self, auth_client):
        """Updating a non-existent comment returns 404."""
        resp = auth_client.patch(
            "/api/comments/99999/", {"body": "body"}, format="json"
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ── Comment Delete ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCommentDelete:
    """Tests for DELETE /api/comments/<id>/delete/."""

    def test_author_can_delete_own_comment(self, auth_client, comment):
        """A comment author can delete their comment."""
        resp = auth_client.delete(f"/api/comments/{comment.id}/delete/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Comment.objects.filter(id=comment.id).exists()

    def test_other_user_cannot_delete_comment(self, api_client, comment, db):
        """A different user cannot delete someone else's comment."""
        other = User.objects.create_user(
            username="other2", email="o2@x.com", password="p"
        )
        api_client.force_authenticate(user=other)
        resp = api_client.delete(f"/api/comments/{comment.id}/delete/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_nonexistent_comment_returns_404(self, auth_client):
        """Deleting a non-existent comment returns 404."""
        resp = auth_client.delete("/api/comments/99999/delete/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ── Comment Vote ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCommentVote:
    """Tests for POST /api/comments/<id>/vote/."""

    def test_like_comment(self, auth_client, comment):
        """Liking a comment increments the likes count."""
        resp = auth_client.post(
            f"/api/comments/{comment.id}/vote/", {"vote": "like"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["likes"] == 1

    def test_dislike_comment(self, auth_client, comment):
        """Disliking a comment increments the dislikes count."""
        resp = auth_client.post(
            f"/api/comments/{comment.id}/vote/", {"vote": "dislike"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["dislikes"] == 1

    def test_voting_same_type_twice_toggles_off(self, auth_client, user, comment):
        """Sending the same vote twice removes the vote (toggle off)."""
        CommentVote.objects.create(
            comment=comment, user=user, vote=CommentVote.VoteType.LIKE
        )
        resp = auth_client.post(
            f"/api/comments/{comment.id}/vote/", {"vote": "like"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["likes"] == 0

    def test_switching_vote_updates_counts(self, auth_client, user, comment):
        """Switching from like to dislike updates both counts correctly."""
        CommentVote.objects.create(
            comment=comment, user=user, vote=CommentVote.VoteType.LIKE
        )
        resp = auth_client.post(
            f"/api/comments/{comment.id}/vote/", {"vote": "dislike"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["likes"] == 0
        assert resp.data["dislikes"] == 1

    def test_invalid_vote_type_returns_400(self, auth_client, comment):
        """An unrecognised vote type is rejected."""
        resp = auth_client.post(
            f"/api/comments/{comment.id}/vote/", {"vote": "invalid"}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_vote_returns_403(self, api_client, comment):
        """Unauthenticated users cannot vote."""
        resp = api_client.post(
            f"/api/comments/{comment.id}/vote/", {"vote": "like"}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_vote_on_nonexistent_comment_returns_404(self, auth_client):
        """Voting on a non-existent comment returns 404."""
        resp = auth_client.post(
            "/api/comments/99999/vote/", {"vote": "like"}, format="json"
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
