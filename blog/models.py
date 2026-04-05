from django.db import models
from django.contrib.auth.models import User


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

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
            models.Index(
                fields=["status", "-created_at"], name="blog_post_status_created_idx"
            ),
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
        ]

    def __str__(self):
        return f"Comment by {self.author} on '{self.post}'"


class CommentVote(models.Model):
    class VoteType(models.TextChoices):
        LIKE = "like", "Like"
        DISLIKE = "dislike", "Dislike"

    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="comment_votes"
    )
    vote = models.CharField(max_length=10, choices=VoteType)

    class Meta:
        unique_together = [("comment", "user")]
        indexes = [
            models.Index(
                fields=["comment", "vote"], name="blog_cvote_comment_vote_idx"
            ),
        ]

    def __str__(self):
        return f"{self.user} {self.vote}d comment #{self.comment_id}"
