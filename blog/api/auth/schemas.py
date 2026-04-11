from datetime import datetime

from ninja import Schema


class ProfileResponse(Schema):
    role: str
    bio: str


class CurrentUserResponse(Schema):
    id: int
    username: str
    date_joined: datetime
    profile: ProfileResponse
    post_count: int
    email: str
    can_manage_tags: bool


class CsrfTokenResponse(Schema):
    csrfToken: str


class DetailResponse(Schema):
    detail: str
