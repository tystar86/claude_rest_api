"""ModelSerializer-based JSON builders shared by Django Ninja routes (no DRF view layer)."""

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers

from accounts.models import Profile
from .models import Comment, CommentVote, Post, Tag
from .utils import build_unique_slug


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
        fields = (*UserSerializer.Meta.fields, "email", "can_manage_tags")


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
            user_id = request.user.id if (request and request.user.is_authenticated) else None
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
        request = self.context.get("request")
        replies = [
            reply
            for reply in obj.replies.all()
            if getattr(reply, "is_approved", True)
            or (
                request is not None
                and request.user.is_authenticated
                and (
                    reply.author_id == request.user.id
                    or reply.post.author_id == request.user.id
                    or request.user.is_superuser
                    or request.user.is_staff
                    or getattr(getattr(request.user, "profile", None), "role", "user")
                    in ("moderator", "admin")
                )
            )
        ]
        return CommentSerializer(replies, many=True, context=self.context).data


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


class PostWriteSerializer(serializers.ModelSerializer):
    """Create (partial=False) or patch (partial=True) posts; input shape is the same."""

    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Post
        fields = ["title", "body", "excerpt", "status", "tag_ids"]
        extra_kwargs = {
            "excerpt": {"required": False, "allow_blank": True, "default": ""},
            "status": {"required": False, "default": Post.Status.DRAFT},
        }

    def validate_tag_ids(self, value):
        if value is None:
            return value
        existing = set(Tag.objects.filter(id__in=value).values_list("id", flat=True))
        missing = sorted(set(value) - existing)
        if missing:
            raise serializers.ValidationError(f"Tag IDs not found: {missing}")
        return value

    def create(self, validated_data):
        tag_ids = validated_data.pop("tag_ids", []) or []
        status_value = validated_data.get("status", Post.Status.DRAFT)
        post = Post.objects.create(
            title=validated_data["title"],
            slug=build_unique_slug(Post, validated_data["title"]),
            author=self.context["request"].user,
            body=validated_data["body"],
            excerpt=validated_data.get("excerpt", ""),
            status=status_value,
            published_at=(timezone.now() if status_value == Post.Status.PUBLISHED else None),
        )
        if tag_ids:
            post.tags.set(Tag.objects.filter(id__in=tag_ids))
        return post

    def update(self, instance, validated_data):
        tag_ids_provided = "tag_ids" in validated_data
        tag_ids = validated_data.pop("tag_ids", None)

        if "title" in validated_data:
            instance.title = validated_data["title"]
            instance.slug = build_unique_slug(Post, instance.title, instance_id=instance.id)
        if "body" in validated_data:
            instance.body = validated_data["body"]
        if "excerpt" in validated_data:
            instance.excerpt = validated_data["excerpt"]
        if (status_value := validated_data.get("status")) is not None:
            instance.status = status_value
            if status_value == Post.Status.PUBLISHED:
                instance.published_at = instance.published_at or timezone.now()
            else:
                instance.published_at = None

        instance.save()

        if tag_ids_provided and tag_ids is not None:
            instance.tags.set(Tag.objects.filter(id__in=tag_ids))

        return instance


class PostDetailSerializer(PostSerializer):
    comments = serializers.SerializerMethodField()

    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields + ["body", "comments"]

    def get_comments(self, obj):
        request = self.context.get("request")
        privileged_roles = ("moderator", "admin")
        top_level = []
        for comment in obj.comments.all():
            if comment.parent_id is not None:
                continue
            if comment.is_approved:
                top_level.append(comment)
                continue
            if (
                request is not None
                and request.user.is_authenticated
                and (
                    comment.author_id == request.user.id
                    or obj.author_id == request.user.id
                    or request.user.is_superuser
                    or request.user.is_staff
                    or getattr(getattr(request.user, "profile", None), "role", "user")
                    in privileged_roles
                )
            ):
                top_level.append(comment)
        return CommentSerializer(top_level, many=True, context=self.context).data
