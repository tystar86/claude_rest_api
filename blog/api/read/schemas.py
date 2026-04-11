from __future__ import annotations

from datetime import datetime

from ninja import Schema


class ProfileResponse(Schema):
    role: str
    bio: str


class UserSummaryResponse(Schema):
    id: int
    username: str
    date_joined: datetime
    profile: ProfileResponse
    post_count: int


class PostTagResponse(Schema):
    id: int
    name: str
    slug: str


class TagSummaryResponse(Schema):
    id: int
    name: str
    slug: str
    post_count: int


class CommentListItemResponse(Schema):
    id: int
    author: str
    post_title: str
    post_slug: str
    body: str
    created_at: datetime
    likes: int
    dislikes: int


class CommentResponse(Schema):
    id: int
    author: str
    body: str
    created_at: datetime
    likes: int
    dislikes: int
    user_vote: str | None
    replies: list["CommentResponse"]


CommentResponse.model_rebuild()


class PostSummaryResponse(Schema):
    id: int
    title: str
    slug: str
    author: str
    excerpt: str
    status: str
    tags: list[PostTagResponse]
    created_at: datetime
    published_at: datetime | None
    comment_count: int | None


class PostDetailResponse(PostSummaryResponse):
    body: str
    comments: list[CommentResponse]


class DashboardStatsResponse(Schema):
    total_posts: int
    comments: int
    authors: int
    active_tags: int
    average_depth_words: int


class DashboardResponse(Schema):
    stats: DashboardStatsResponse
    latest_posts: list[PostSummaryResponse]
    most_commented_posts: list[PostSummaryResponse]
    most_used_tags: list[TagSummaryResponse]
    top_authors: list[UserSummaryResponse]


class PaginatedCommentsResponse(Schema):
    count: int
    total_pages: int
    page: int
    results: list[CommentListItemResponse]


class PaginatedPostsResponse(Schema):
    count: int
    total_pages: int
    page: int
    results: list[PostSummaryResponse]


class PaginatedTagsResponse(Schema):
    count: int
    total_pages: int
    page: int
    results: list[TagSummaryResponse]


class PaginatedUsersResponse(Schema):
    count: int
    total_pages: int
    page: int
    results: list[UserSummaryResponse]


class TagDetailResponse(PaginatedPostsResponse):
    tag: TagSummaryResponse


class UserDetailResponse(PaginatedPostsResponse):
    user: UserSummaryResponse
