from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import Profile
from .models import Comment, Post, Tag


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["role"]


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    post_count = serializers.IntegerField(source="posts.count", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "date_joined", "profile", "post_count"]


class TagSerializer(serializers.ModelSerializer):
    post_count = serializers.IntegerField(source="posts.count", read_only=True)

    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "post_count"]


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "author", "body", "created_at", "replies"]

    def get_replies(self, obj):
        return CommentSerializer(obj.replies.all(), many=True).data


class PostSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()
    tags = TagSerializer(many=True, read_only=True)

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
        return CommentSerializer(top_level, many=True).data
