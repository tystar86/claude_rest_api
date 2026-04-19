"""Unit tests for the dashboard API endpoint."""

from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from blog.models import Comment, CommentVote, Post, Tag


@pytest.mark.django_db
class TestDashboardView:
    """Tests for GET /api/dashboard/."""

    def test_returns_200_for_anonymous(self, api_client):
        """Anyone can access the dashboard."""
        resp = api_client.get("/api/dashboard/")
        assert resp.status_code == 200

    def test_head_returns_200(self, api_client):
        """HEAD is supported for cache / link checking without a body."""
        resp = api_client.head("/api/dashboard/")
        assert resp.status_code == 200

    def test_response_contains_top_level_keys(self, api_client):
        """Response includes all expected top-level sections."""
        data = api_client.get("/api/dashboard/").json()
        assert "stats" in data
        assert "latest_posts" in data
        assert "most_commented_posts" in data
        assert "most_liked_posts" in data
        assert "most_used_tags" in data
        assert "top_authors" in data
        assert "activity" not in data

    def test_stats_contains_expected_fields(self, api_client):
        """stats section exposes all expected counters."""
        stats = api_client.get("/api/dashboard/").json()["stats"]
        assert "total_posts" in stats
        assert "comments" in stats
        assert "authors" in stats
        assert "active_tags" in stats
        assert "new_posts_7d" in stats

    def test_stats_reflect_created_content(self, api_client, post, comment):
        """Stats accurately count existing posts and comments."""
        data = api_client.get("/api/dashboard/").json()
        stats = data["stats"]
        assert stats["total_posts"] >= 1
        assert stats["new_posts_7d"] >= 1
        assert stats["comments"] >= 1
        assert "activity" not in data
        act = api_client.get("/api/activity/").json()
        assert act["latest_post_title"] == post.title
        assert act["latest_comment_author"] == comment.author.username

    def test_most_liked_posts_ranks_by_comment_upvotes(self, api_client, db, post, comment, user):
        """most_liked_posts lists posts with at least one comment like, ordered by like total."""
        other = User.objects.create_user(username="liker", email="liker@x.com", password="p")
        CommentVote.objects.create(user=other, comment=comment, vote=CommentVote.VoteType.LIKE)
        data = api_client.get("/api/dashboard/").json()
        liked = data["most_liked_posts"]
        assert len(liked) >= 1
        first = next(p for p in liked if p["slug"] == post.slug)
        assert first["like_count"] >= 1

    def test_most_commented_posts_include_accurate_comment_count(
        self, api_client, db, post, user, comment
    ):
        """most_commented_posts comment_count matches all comments on published posts."""
        u2 = User.objects.create_user(username="c2", email="c2@x.com", password="p")
        u3 = User.objects.create_user(username="c3", email="c3@x.com", password="p")
        Comment.objects.create(post=post, author=u2, body="Second.", is_approved=True)
        Comment.objects.create(post=post, author=u3, body="Third.", is_approved=True)
        Comment.objects.create(post=post, author=u3, body="Pending.", is_approved=False)
        data = api_client.get("/api/dashboard/").json()
        row = next(p for p in data["most_commented_posts"] if p["slug"] == post.slug)
        # 1 from `comment` fixture + 3 more (including unapproved)
        assert row["comment_count"] == 4

    def test_post_summary_lists_include_comment_count_and_like_count(
        self, api_client, post, comment, user
    ):
        """latest_posts, most_commented_posts, and most_liked_posts expose count fields for the UI."""
        other = User.objects.create_user(username="voter", email="voter@x.com", password="p")
        CommentVote.objects.create(user=other, comment=comment, vote=CommentVote.VoteType.LIKE)
        data = api_client.get("/api/dashboard/").json()
        for key in ("latest_posts", "most_commented_posts", "most_liked_posts"):
            items = data[key]
            assert isinstance(items, list)
            for item in items:
                assert "comment_count" in item
                assert "like_count" in item
                assert isinstance(item["comment_count"], int)
                assert isinstance(item["like_count"], int)

    def test_empty_database_returns_zero_stats(self, api_client, db):
        """All counters are 0 on an empty database."""
        data = api_client.get("/api/dashboard/").json()
        stats = data["stats"]
        assert stats["total_posts"] == 0
        assert stats["comments"] == 0
        assert stats["authors"] == 0
        assert stats["active_tags"] == 0
        assert stats["new_posts_7d"] == 0
        assert "activity" not in data
        act = api_client.get("/api/activity/").json()
        assert act["latest_post_title"] is None
        assert act["latest_comment_at"] is None
        assert act["latest_user_username"] is None

    def test_latest_posts_is_list(self, api_client):
        """latest_posts is always a list."""
        data = api_client.get("/api/dashboard/").json()
        assert isinstance(data["latest_posts"], list)

    def test_top_authors_only_includes_authors_with_posts(self, api_client, post):
        """top_authors only lists users who have at least one post."""
        data = api_client.get("/api/dashboard/").json()
        for author in data["top_authors"]:
            assert author["post_count"] > 0

    def test_new_posts_7d_excludes_published_before_window(self, api_client, db, user):
        """Posts first published more than 7 days ago do not count toward new_posts_7d."""
        old = timezone.now() - timedelta(days=10)
        p = Post.objects.create(
            title="Stale",
            slug="stale-post",
            author=user,
            body="Body.",
            status=Post.Status.PUBLISHED,
            published_at=old,
        )
        Post.objects.filter(pk=p.pk).update(created_at=old)
        data = api_client.get("/api/dashboard/").json()
        assert data["stats"]["new_posts_7d"] == 0

    def test_stats_comments_include_unapproved_on_published_posts(
        self, api_client, db, post, user, comment
    ):
        """Unapproved comments on published posts count toward stats.comments."""
        Comment.objects.create(
            post=post,
            author=user,
            body="Pending moderation.",
            is_approved=False,
        )
        data = api_client.get("/api/dashboard/").json()
        assert data["stats"]["comments"] == 2

    def test_draft_post_comments_excluded_from_comment_count(self, api_client, db):
        """Comments on draft posts are not counted in the stats comment total."""
        author = User.objects.create_user(
            username="draftauthor", email="draftauthor@x.com", password="p"
        )
        draft = Post.objects.create(
            title="Draft Only",
            slug="draft-only",
            author=author,
            body="Draft body.",
            status=Post.Status.DRAFT,
        )
        Comment.objects.create(
            post=draft,
            author=author,
            body="Comment on draft.",
            is_approved=True,
        )
        resp = api_client.get("/api/dashboard/")
        assert resp.status_code == 200
        assert resp.json()["stats"]["comments"] == 0

    def test_most_used_tags_excludes_draft_posts(self, api_client, db):
        """Tags attached only to draft posts appear with a post_count of 0 or are absent."""
        author = User.objects.create_user(
            username="tagdraftauthor", email="tagdraftauthor@x.com", password="p"
        )
        tag = Tag.objects.create(name="DraftTag", slug="draft-tag")
        draft = Post.objects.create(
            title="Draft Tagged",
            slug="draft-tagged",
            author=author,
            body="Draft body.",
            status=Post.Status.DRAFT,
        )
        draft.tags.add(tag)
        data = api_client.get("/api/dashboard/").json()
        tag_entries = [t for t in data["most_used_tags"] if t["slug"] == tag.slug]
        assert not tag_entries or tag_entries[0]["post_count"] == 0

    def test_top_authors_excludes_draft_only_authors(self, api_client, db):
        """Users who only have draft posts do not appear in top_authors."""
        draft_author = User.objects.create_user(
            username="draftonlyauthor", email="draftonlyauthor@x.com", password="p"
        )
        Post.objects.create(
            title="Only Draft",
            slug="only-draft",
            author=draft_author,
            body="Draft body.",
            status=Post.Status.DRAFT,
        )
        data = api_client.get("/api/dashboard/").json()
        author_usernames = [a["username"] for a in data["top_authors"]]
        assert draft_author.username not in author_usernames
