"""Read-side JSON serializers for Django Ninja routes. Post writes use ``blog.services``."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Comment, CommentVote, Post, Tag

User = get_user_model()


def _dt(value):
    if value is None:
        return None
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value.isoformat()


class _ReadSerializer:
    """Minimal read serializer with DRF-like ``instance`` / ``many`` / ``context`` / ``.data``."""

    def __init__(
        self,
        instance=None,
        data=None,
        partial: bool = False,
        many: bool = False,
        context: dict | None = None,
    ):
        self.instance = instance
        self.initial_data = data
        self.partial = partial
        self.many = many
        self.context = context or {}

    @property
    def data(self) -> list | dict:
        if self.many:
            return [self.to_representation(x) for x in self.instance]
        return self.to_representation(self.instance)

    def to_representation(self, obj) -> dict:
        raise NotImplementedError


class UserSerializer(_ReadSerializer):
    def to_representation(self, obj: User) -> dict:
        if hasattr(obj, "post_count"):
            post_count = obj.post_count
        else:
            post_count = Post.published.filter(author=obj).count()
        return {
            "id": obj.id,
            "username": obj.username,
            "date_joined": _dt(obj.date_joined),
            "profile": {"role": obj.role, "bio": obj.bio or ""},
            "post_count": post_count,
        }


class CurrentUserSerializer(UserSerializer):
    def to_representation(self, obj: User) -> dict:
        data = super().to_representation(obj)
        role = obj.role
        data["email"] = obj.email
        data["can_manage_tags"] = bool(
            obj.is_superuser or obj.is_staff or role in ("moderator", "admin")
        )
        return data


class PostTagSerializer(_ReadSerializer):
    def to_representation(self, obj: Tag) -> dict:
        return {"id": obj.id, "name": obj.name, "slug": obj.slug}


class TagSerializer(_ReadSerializer):
    def to_representation(self, obj: Tag) -> dict:
        if hasattr(obj, "post_count"):
            post_count = obj.post_count
        else:
            post_count = obj.posts.count()
        return {
            "id": obj.id,
            "name": obj.name,
            "slug": obj.slug,
            "post_count": post_count,
        }


class CommentSerializer(_ReadSerializer):
    def to_representation(self, obj: Comment) -> dict:
        return {
            "id": obj.id,
            "author": str(obj.author),
            "body": obj.body,
            "created_at": _dt(obj.created_at),
            "likes": self._likes(obj),
            "dislikes": self._dislikes(obj),
            "user_vote": self._user_vote(obj),
            "replies": self._replies(obj),
        }

    def _vote_tuple(self, obj: Comment) -> tuple[int, int, str | None]:
        if not hasattr(self, "_vote_cache"):
            self._vote_cache: dict[int, tuple[int, int, str | None]] = {}
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

    def _likes(self, obj: Comment) -> int:
        return self._vote_tuple(obj)[0]

    def _dislikes(self, obj: Comment) -> int:
        return self._vote_tuple(obj)[1]

    def _user_vote(self, obj: Comment) -> str | None:
        return self._vote_tuple(obj)[2]

    def _replies(self, obj: Comment) -> list[dict]:
        replies = list(obj.replies.all())
        return CommentSerializer(replies, many=True, context=self.context).data


class CommentListSerializer(_ReadSerializer):
    def to_representation(self, obj: Comment) -> dict:
        likes = dislikes = 0
        for v in obj.votes.all():
            if v.vote == CommentVote.VoteType.LIKE:
                likes += 1
            else:
                dislikes += 1
        return {
            "id": obj.id,
            "author": str(obj.author),
            "post_title": obj.post.title,
            "post_slug": obj.post.slug,
            "body": obj.body,
            "created_at": _dt(obj.created_at),
            "likes": likes,
            "dislikes": dislikes,
        }


class PostSerializer(_ReadSerializer):
    def to_representation(self, obj: Post) -> dict:
        comment_count = getattr(obj, "comment_count", None)
        if comment_count is None:
            comment_count = obj.comments.count()
        like_count = getattr(obj, "comment_like_count", None)
        if like_count is None:
            like_count = 0
        return {
            "id": obj.id,
            "title": obj.title,
            "slug": obj.slug,
            "author": str(obj.author),
            "excerpt": obj.excerpt,
            "status": obj.status,
            "tags": PostTagSerializer(obj.tags.all(), many=True).data,
            "created_at": _dt(obj.created_at),
            "published_at": _dt(obj.published_at),
            "comment_count": comment_count,
            "like_count": like_count,
        }


class PostDetailSerializer(PostSerializer):
    def to_representation(self, obj: Post) -> dict:
        data = super().to_representation(obj)
        data["body"] = obj.body
        top_level: list[Comment] = []
        for comment in obj.comments.all():
            if comment.parent_id is not None:
                continue
            top_level.append(comment)
        data["comments"] = CommentSerializer(top_level, many=True, context=self.context).data
        return data
