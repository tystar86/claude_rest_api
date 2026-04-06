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
    post_count = serializers.SerializerMethodField()

    def get_post_count(self, obj):
        if hasattr(obj, "post_count"):
            return obj.post_count
        return obj.posts.count()

    class Meta:
        model = User
        fields = ("id", "username", "date_joined", "profile", "post_count")


class CurrentUserSerializer(UserSerializer):
    can_manage_tags = serializers.SerializerMethodField()

    def get_can_manage_tags(self, obj):
        if obj.is_superuser or obj.is_staff:
            return True
        role = getattr(getattr(obj, "profile", None), "role", "user")
        return role in ("moderator", "admin")

    class Meta(UserSerializer.Meta):
        # email is only exposed to the authenticated user for their own data
        fields = UserSerializer.Meta.fields + ("email", "can_manage_tags")


class PostTagSerializer(serializers.ModelSerializer):
    """Lightweight tag serializer for use inside PostSerializer (no post_count)."""

    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


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

    def _get_vote_data(self, obj):
        """Single pass over votes queryset; results cached per comment pk."""
        if not hasattr(self, "_vote_cache"):
            self._vote_cache = {}
        if obj.pk not in self._vote_cache:
            likes = dislikes = 0
            user_vote = None
            request = self.context.get("request")
            user_id = (
                request.user.id if (request and request.user.is_authenticated) else None
            )
            for v in obj.votes.all():
                if v.vote == CommentVote.VoteType.LIKE:
                    likes += 1
                else:
                    dislikes += 1
                if user_id and v.user_id == user_id:
                    user_vote = v.vote
            self._vote_cache[obj.pk] = (likes, dislikes, user_vote)
        return self._vote_cache[obj.pk]

    def get_likes(self, obj):
        return self._get_vote_data(obj)[0]

    def get_dislikes(self, obj):
        return self._get_vote_data(obj)[1]

    def get_user_vote(self, obj):
        return self._get_vote_data(obj)[2]

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

    def _get_vote_data(self, obj):
        """Single pass over votes queryset; results cached per comment pk."""
        if not hasattr(self, "_vote_cache"):
            self._vote_cache = {}
        if obj.pk not in self._vote_cache:
            likes = dislikes = 0
            for v in obj.votes.all():
                if v.vote == CommentVote.VoteType.LIKE:
                    likes += 1
                else:
                    dislikes += 1
            self._vote_cache[obj.pk] = (likes, dislikes)
        return self._vote_cache[obj.pk]

    def get_likes(self, obj):
        return self._get_vote_data(obj)[0]

    def get_dislikes(self, obj):
        return self._get_vote_data(obj)[1]


class PostSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()
    tags = PostTagSerializer(many=True, read_only=True)
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
        top_level = [c for c in obj.comments.all() if c.parent_id is None]
        return CommentSerializer(top_level, many=True, context=self.context).data
