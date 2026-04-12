"""Verify Ninja response schemas stay aligned with serializer output.

Each test serializes a model instance through the shared ModelSerializer then
validates the result against the corresponding Ninja Pydantic schema.  A
failure means the two layers have drifted and the API contract is at risk.
"""

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.db.models import Count, Q
from django.test import RequestFactory

from blog.api.auth.schemas import CurrentUserResponse
from blog.api.data.schemas import (
    CommentListItemResponse,
    CommentResponse,
    DashboardResponse,
    PaginatedCommentsResponse,
    PaginatedPostsResponse,
    PaginatedTagsResponse,
    PaginatedUsersResponse,
    PostDetailResponse,
    PostSummaryResponse,
    TagDetailResponse,
    TagSummaryResponse,
    UserDetailResponse,
    UserSummaryResponse,
)
from blog.models import Comment, Post, Tag
from blog.serializers import (
    CommentListSerializer,
    CommentSerializer,
    CurrentUserSerializer,
    PostDetailSerializer,
    PostSerializer,
    TagSerializer,
    UserSerializer,
)
from blog import api_views


def _anon_request():
    factory = RequestFactory()
    request = factory.get("/")
    request.user = AnonymousUser()
    return request


@pytest.mark.django_db
class TestCurrentUserSchemaContract:
    def test_serialized_user_validates_against_ninja_schema(self, user):
        payload = dict(CurrentUserSerializer(user).data)
        validated = CurrentUserResponse(**payload)
        assert validated.username == user.username
        assert validated.email == user.email
        assert validated.can_manage_tags is False

    def test_moderator_payload_validates(self, moderator):
        payload = dict(CurrentUserSerializer(moderator).data)
        validated = CurrentUserResponse(**payload)
        assert validated.can_manage_tags is True


@pytest.mark.django_db
class TestPostSchemaContract:
    def test_post_summary_validates(self, post):
        data = PostSerializer(post).data
        validated = PostSummaryResponse(**data)
        assert validated.slug == post.slug

    def test_post_detail_validates(self, post, comment):
        request = _anon_request()
        data = PostDetailSerializer(post, context={"request": request}).data
        validated = PostDetailResponse(**data)
        assert validated.slug == post.slug
        assert len(validated.comments) >= 1


@pytest.mark.django_db
class TestCommentSchemaContract:
    def test_comment_list_item_validates(self, comment):
        data = CommentListSerializer(comment).data
        validated = CommentListItemResponse(**data)
        assert validated.id == comment.id

    def test_comment_response_validates(self, comment):
        request = _anon_request()
        data = CommentSerializer(comment, context={"request": request}).data
        validated = CommentResponse(**data)
        assert validated.id == comment.id


@pytest.mark.django_db
class TestTagSchemaContract:
    def test_tag_validates(self, tag):
        data = TagSerializer(tag).data
        validated = TagSummaryResponse(**data)
        assert validated.slug == tag.slug


@pytest.mark.django_db
class TestUserSchemaContract:
    def test_user_validates(self, user):
        data = UserSerializer(user).data
        validated = UserSummaryResponse(**data)
        assert validated.username == user.username


@pytest.mark.django_db
class TestPaginationSchemaContract:
    def _make_request(self, page="1"):
        factory = RequestFactory()
        return factory.get("/", {"page": page})

    def test_paginated_posts_validates(self, post):
        request = self._make_request()
        data = api_views.paginate(
            Post.objects.filter(status=Post.Status.PUBLISHED),
            request,
            PostSerializer,
        )
        validated = PaginatedPostsResponse(**data)
        assert validated.count >= 1
        assert validated.page == 1

    def test_paginated_tags_validates(self, tag):
        request = self._make_request()
        qs = Tag.objects.annotate(
            post_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
        )
        data = api_views.paginate(qs, request, TagSerializer)
        validated = PaginatedTagsResponse(**data)
        assert validated.count >= 1

    def test_paginated_users_validates(self, user):
        request = self._make_request()
        qs = User.objects.select_related("profile").annotate(
            post_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
        )
        data = api_views.paginate(qs, request, UserSerializer)
        validated = PaginatedUsersResponse(**data)
        assert validated.count >= 1

    def test_paginated_comments_validates(self, comment):
        request = self._make_request()
        qs = (
            Comment.objects.filter(post__status=Post.Status.PUBLISHED, is_approved=True)
            .select_related("author", "post")
            .prefetch_related("votes")
        )
        data = api_views.paginate(qs, request, CommentListSerializer)
        validated = PaginatedCommentsResponse(**data)
        assert validated.count >= 1


@pytest.mark.django_db
class TestDashboardSchemaContract:
    def test_dashboard_payload_validates(self, post, comment):
        data = api_views.build_dashboard_payload()
        validated = DashboardResponse(**data)
        assert validated.stats.total_posts >= 1


@pytest.mark.django_db
class TestTagDetailSchemaContract:
    def test_tag_detail_validates(self, tag, post):
        post.tags.add(tag)
        request = _anon_request()
        annotated_tag = Tag.objects.annotate(
            post_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
        ).get(pk=tag.pk)
        tag_data = TagSerializer(annotated_tag).data
        posts_data = api_views.paginate(
            Post.objects.filter(tags=tag, status=Post.Status.PUBLISHED),
            request,
            PostSerializer,
        )
        payload = {"tag": tag_data, **posts_data}
        validated = TagDetailResponse(**payload)
        assert validated.tag.slug == tag.slug
        assert validated.count >= 1


@pytest.mark.django_db
class TestUserDetailSchemaContract:
    def test_user_detail_validates(self, user, post):
        request = _anon_request()
        annotated_user = (
            User.objects.select_related("profile")
            .annotate(post_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED)))
            .get(pk=user.pk)
        )
        user_data = UserSerializer(annotated_user).data
        posts_data = api_views.paginate(
            Post.objects.filter(author=user, status=Post.Status.PUBLISHED),
            request,
            PostSerializer,
        )
        payload = {"user": user_data, **posts_data}
        validated = UserDetailResponse(**payload)
        assert validated.user.username == user.username
