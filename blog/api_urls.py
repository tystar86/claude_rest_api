from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from .api import (
    preview_auth_api,
    preview_read_api,
    public_auth_api,
    public_read_callbacks,
)
from . import api_views


def _get_or_drf(get_view, fallback_view):
    @csrf_exempt
    def view(request, *args, **kwargs):
        if request.method == "GET":
            return get_view(request, *args, **kwargs)
        return fallback_view(request, *args, **kwargs)

    return view


urlpatterns = [
    path("auth/", public_auth_api.urls),
    path("_ninja/auth/", preview_auth_api.urls),
    path("_ninja/read/", preview_read_api.urls),
    path("dashboard/", public_read_callbacks["dashboard"]),
    path("comments/", public_read_callbacks["comment_list"]),
    path("posts/<slug:slug>/comments/", api_views.comment_create),
    path(
        "posts/", _get_or_drf(public_read_callbacks["post_list"], api_views.post_list)
    ),
    path(
        "posts/<slug:slug>/",
        _get_or_drf(public_read_callbacks["post_detail"], api_views.post_detail),
    ),
    path("tags/", _get_or_drf(public_read_callbacks["tag_list"], api_views.tag_list)),
    path(
        "tags/<slug:slug>/",
        _get_or_drf(public_read_callbacks["tag_detail"], api_views.tag_detail),
    ),
    path("users/", public_read_callbacks["user_list"]),
    path("users/<str:username>/comments/", public_read_callbacks["user_comments"]),
    path("users/<str:username>/", public_read_callbacks["user_detail"]),
    path("auth/login/", api_views.login_view),
    path("auth/register/", api_views.register_view),
    path("auth/resend-verification/", api_views.resend_verification_view),
    path("auth/profile/", api_views.update_profile),
    path("comments/<int:comment_id>/vote/", api_views.comment_vote),
    path("comments/<int:comment_id>/", api_views.comment_update),
    path("comments/<int:comment_id>/delete/", api_views.comment_delete),
]
