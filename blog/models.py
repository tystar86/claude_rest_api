from django.db import models
from django.contrib.auth import get_user_model

from django.db.models import Count, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce

User = get_user_model()


class PublishedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Post.Status.PUBLISHED).order_by("-published_at")

    def list_qs(self):
        """Published posts annotated for list-card serialization: body deferred, comment count included."""
        comment_count_sq = (
            Comment.objects.filter(post=OuterRef("pk"))
            .order_by()
            .values("post")
            .annotate(cnt=Count("id"))
            .values("cnt")
        )
        return (
            self.get_queryset()
            .defer("body")
            .select_related("author")
            .prefetch_related("tags")
            .annotate(
                comment_count=Coalesce(Subquery(comment_count_sq, output_field=IntegerField()), 0)
            )
        )


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    objects = models.Manager()
    published = PublishedManager()

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    body = models.TextField()
    excerpt = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status, default=Status.DRAFT)
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["author"]),
            models.Index(fields=["status", "-created_at"], name="blog_post_status_created_idx"),
        ]

    def __str__(self):
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    body = models.TextField()
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["-created_at"], name="blog_comment_created_idx"),
            models.Index(fields=["post", "created_at"], name="blog_comment_post_created_idx"),
            models.Index(
                fields=["post"],
                condition=models.Q(is_approved=True),
                name="blog_comment_post_approved_idx",
            ),
        ]

    def __str__(self):
        return f"Comment by {self.author} on '{self.post}'"


class CommentVote(models.Model):
    class VoteType(models.TextChoices):
        LIKE = "like", "Like"
        DISLIKE = "dislike", "Dislike"

    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comment_votes")
    vote = models.CharField(max_length=10, choices=VoteType)

    class Meta:
        unique_together = [("comment", "user")]
        indexes = [
            models.Index(fields=["comment", "vote"], name="blog_cvote_comment_vote_idx"),
        ]

    def __str__(self):
        return f"{self.user} {self.vote}d comment #{self.comment_id}"
