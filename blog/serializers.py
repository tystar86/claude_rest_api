from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import Profile
from .models import Comment, CommentVote, Post, Tag


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("role", "bio")


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    post_count = serializers.IntegerField(source="posts.count", read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "date_joined", "profile", "post_count")


class CurrentUserSerializer(UserSerializer):
    can_manage_tags = serializers.SerializerMethodField()

    def get_can_manage_tags(self, obj):
        if obj.is_superuser or obj.is_staff:
            return True
        role = getattr(getattr(obj, "profile", None), "role", "user")
        return role in ("moderator", "admin")

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ("can_manage_tags",)


class TagSerializer(serializers.ModelSerializer):
    post_count = serializers.SerializerMethodField()

    def get_post_count(self, obj):
        # Use pre-annotated value (e.g. published-only count from dashboard view)
        # when present; fall back to the full related manager count elsewhere.
        if hasattr(obj, "post_count"):
            return obj.post_count
        return obj.posts.count()

    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "post_count"]


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()
    replies = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()
    dislikes = serializers.SerializerMethodField()
    user_vote = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "author",
            "body",
            "created_at",
            "likes",
            "dislikes",
            "user_vote",
            "replies",
        ]

    def get_likes(self, obj):
        return obj.votes.filter(vote=CommentVote.VoteType.LIKE).count()

    def get_dislikes(self, obj):
        return obj.votes.filter(vote=CommentVote.VoteType.DISLIKE).count()

    def get_user_vote(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        vote = obj.votes.filter(user=request.user).first()
        return vote.vote if vote else None

    def get_replies(self, obj):
        return CommentSerializer(
            obj.replies.all(), many=True, context=self.context
        ).data


class CommentListSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()
    post_title = serializers.CharField(source="post.title", read_only=True)
    post_slug = serializers.CharField(source="post.slug", read_only=True)
    likes = serializers.SerializerMethodField()
    dislikes = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "author",
            "post_title",
            "post_slug",
            "body",
            "created_at",
            "likes",
            "dislikes",
        ]

    def get_likes(self, obj):
        return obj.votes.filter(vote=CommentVote.VoteType.LIKE).count()

    def get_dislikes(self, obj):
        return obj.votes.filter(vote=CommentVote.VoteType.DISLIKE).count()


class PostSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()
    tags = TagSerializer(many=True, read_only=True)
    comment_count = serializers.IntegerField(read_only=True, default=None)

    class Meta:
        model = Post
        fields = [
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
        ]


class PostDetailSerializer(PostSerializer):
    comments = serializers.SerializerMethodField()

    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields + ["body", "comments"]

    def get_comments(self, obj):
        top_level = (
            obj.comments.filter(parent=None)
            .select_related("author")
            .prefetch_related("replies__author")
        )
        return CommentSerializer(top_level, many=True, context=self.context).data
