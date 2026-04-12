from django.urls import path
from django.http import HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt

from .api import (
    preview_auth_api,
    preview_read_api,
    preview_write_api,
    public_auth_api,
    public_read_callbacks,
    public_write_callbacks,
)


def _dispatch_by_method(**method_views):
    @csrf_exempt
    def view(request, *args, **kwargs):
        handler = method_views.get(request.method)
        if handler is None:
            return HttpResponseNotAllowed(method_views.keys())
        return handler(request, *args, **kwargs)

    return view


urlpatterns = [
    path("auth/", public_auth_api.urls),
    path("_ninja/auth/", preview_auth_api.urls),
    path("_ninja/read/", preview_read_api.urls),
    path("_ninja/write/", preview_write_api.urls),
    path("dashboard/", public_read_callbacks["dashboard"]),
    path("comments/", public_read_callbacks["comment_list"]),
    path("posts/<slug:slug>/comments/", public_write_callbacks["comment_create"]),
    path(
        "posts/",
        _dispatch_by_method(
            GET=public_read_callbacks["post_list"],
            POST=public_write_callbacks["create_post"],
        ),
    ),
    path(
        "posts/<slug:slug>/",
        _dispatch_by_method(
            GET=public_read_callbacks["post_detail"],
            PATCH=public_write_callbacks["update_post"],
            DELETE=public_write_callbacks["delete_post"],
        ),
    ),
    path(
        "tags/",
        _dispatch_by_method(
            GET=public_read_callbacks["tag_list"],
            POST=public_write_callbacks["create_tag"],
        ),
    ),
    path(
        "tags/<slug:slug>/",
        _dispatch_by_method(
            GET=public_read_callbacks["tag_detail"],
            PATCH=public_write_callbacks["update_tag"],
            DELETE=public_write_callbacks["delete_tag"],
        ),
    ),
    path("users/", public_read_callbacks["user_list"]),
    path("users/<str:username>/comments/", public_read_callbacks["user_comments"]),
    path("users/<str:username>/", public_read_callbacks["user_detail"]),
    path("auth/login/", public_write_callbacks["login"]),
    path("auth/register/", public_write_callbacks["register"]),
    path("auth/resend-verification/", public_write_callbacks["resend_verification"]),
    path("auth/profile/", public_write_callbacks["update_profile"]),
    path("comments/<int:comment_id>/vote/", public_write_callbacks["comment_vote"]),
    path("comments/<int:comment_id>/", public_write_callbacks["comment_update"]),
    path("comments/<int:comment_id>/delete/", public_write_callbacks["comment_delete"]),
]
