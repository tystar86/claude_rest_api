from django.urls import path

from .api import (
    preview_auth_api,
    preview_read_api,
    preview_write_api,
    public_auth_api,
    public_read_callbacks,
    public_write_callbacks,
)
from .api.auth.services import json_compat_response


def _dispatch_by_method(**method_views):
    def view(request, *args, **kwargs):
        is_head_fallback = request.method == "HEAD" and "HEAD" not in method_views
        lookup_method = "GET" if is_head_fallback else request.method
        handler = method_views.get(lookup_method)
        if handler is None:
            allowed_methods = sorted(set(method_views.keys()))
            if "GET" in allowed_methods and "HEAD" not in allowed_methods:
                allowed_methods.append("HEAD")
            response = json_compat_response(
                {"detail": "Method not allowed."}, status=405
            )
            response["Allow"] = ", ".join(allowed_methods)
            return response
        if is_head_fallback:
            original_method = request.method
            request.method = "GET"
            try:
                return handler(request, *args, **kwargs)
            finally:
                request.method = original_method
        return handler(request, *args, **kwargs)

    return view


urlpatterns = [
    path("auth/", public_auth_api.urls),
    path("_ninja/auth/", preview_auth_api.urls),
    path("_ninja/read/", preview_read_api.urls),
    path("_ninja/write/", preview_write_api.urls),
    path("dashboard/", public_read_callbacks["dashboard"]),
    path("comments/", public_read_callbacks["comment_list"]),
    path(
        "posts/<slug:slug>/comments/",
        _dispatch_by_method(POST=public_write_callbacks["comment_create"]),
    ),
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
    path("auth/login/", _dispatch_by_method(POST=public_write_callbacks["login"])),
    path(
        "auth/register/", _dispatch_by_method(POST=public_write_callbacks["register"])
    ),
    path(
        "auth/resend-verification/",
        _dispatch_by_method(POST=public_write_callbacks["resend_verification"]),
    ),
    path(
        "auth/profile/",
        _dispatch_by_method(PATCH=public_write_callbacks["update_profile"]),
    ),
    path(
        "comments/<int:comment_id>/vote/",
        _dispatch_by_method(POST=public_write_callbacks["comment_vote"]),
    ),
    path(
        "comments/<int:comment_id>/",
        _dispatch_by_method(PATCH=public_write_callbacks["comment_update"]),
    ),
    path(
        "comments/<int:comment_id>/delete/",
        _dispatch_by_method(DELETE=public_write_callbacks["comment_delete"]),
    ),
]
