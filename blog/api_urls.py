from django.urls import path

from . import api_views

urlpatterns = [
    path("dashboard/", api_views.dashboard),
    path("comments/", api_views.comment_list),
    path("posts/<slug:slug>/comments/", api_views.comment_create),
    path("posts/", api_views.post_list),
    path("posts/<slug:slug>/", api_views.post_detail),
    path("tags/", api_views.tag_list),
    path("tags/<slug:slug>/", api_views.tag_detail),
    path("users/", api_views.user_list),
    path("users/<str:username>/comments/", api_views.user_comments),
    path("users/<str:username>/", api_views.user_detail),
    path("auth/csrf/", api_views.csrf),
    path("auth/login/", api_views.login_view),
    path("auth/register/", api_views.register_view),
    path("auth/logout/", api_views.logout_view),
    path("auth/resend-verification/", api_views.resend_verification_view),
    path("auth/user/", api_views.current_user),
    path("auth/profile/", api_views.update_profile),
    path("comments/<int:comment_id>/vote/", api_views.comment_vote),
    path("comments/<int:comment_id>/", api_views.comment_update),
    path("comments/<int:comment_id>/delete/", api_views.comment_delete),
]
