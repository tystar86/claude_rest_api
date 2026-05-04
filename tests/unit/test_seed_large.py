from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.models import Count

import pytest

from blog.management.commands import seed_large
from blog.models import Comment, CommentVote, Post


def test_allocate_weighted_counts_preserves_total_and_skew():
    counts = seed_large._allocate_weighted_counts([6.0, 3.0, 1.0, 0.5], 120)

    assert sum(counts) == 120
    assert counts[0] > counts[1] > counts[2] > counts[3]


@pytest.mark.django_db(transaction=True)
def test_seed_large_creates_realistic_skewed_dataset(monkeypatch):
    monkeypatch.setattr(seed_large, "SEED_USER_COUNT", 24)
    monkeypatch.setattr(seed_large, "SEED_POST_TARGET", 120)

    call_command("seed_large", "--clear", "--seed", "11", verbosity=0)

    User = get_user_model()
    seeded_users = list(
        User.objects.filter(email__iendswith=f"@{seed_large.SEED_EMAIL_DOMAIN}").order_by(
            "username"
        )
    )
    seeded_posts = Post.objects.filter(author__in=seeded_users)
    per_author_totals = list(
        seeded_posts.values("author_id").annotate(total=Count("id")).values_list("total", flat=True)
    )

    assert len(seeded_users) == 24
    assert seeded_posts.count() == 120
    assert all(not user.username.startswith("techuser_") for user in seeded_users)
    assert all(user.email.endswith(f"@{seed_large.SEED_EMAIL_DOMAIN}") for user in seeded_users)
    assert any(("." in user.username) or ("-" in user.username) for user in seeded_users)
    assert len(set(per_author_totals)) > 1
    assert seeded_posts.filter(status=Post.Status.PUBLISHED).exists()
    assert seeded_posts.filter(status=Post.Status.DRAFT).exists()
    assert Comment.objects.filter(post__in=seeded_posts).exists()
    assert Comment.objects.filter(post__in=seeded_posts, is_approved=False).exists()
    assert CommentVote.objects.filter(comment__post__in=seeded_posts).exists()


@pytest.mark.django_db(transaction=True)
def test_clear_removes_only_seeded_users(monkeypatch):
    monkeypatch.setattr(seed_large, "SEED_USER_COUNT", 10)
    monkeypatch.setattr(seed_large, "SEED_POST_TARGET", 24)

    User = get_user_model()
    existing_user = User.objects.create_user(
        username="existing.user",
        email="existing@example.com",
        password="test-pass",
    )

    call_command("seed_large", "--seed", "5", verbosity=0)
    assert User.objects.filter(email__iendswith=f"@{seed_large.SEED_EMAIL_DOMAIN}").count() == 10

    seed_large.Command()._clear()

    assert User.objects.filter(email__iendswith=f"@{seed_large.SEED_EMAIL_DOMAIN}").count() == 0
    assert User.objects.filter(pk=existing_user.pk).exists()
