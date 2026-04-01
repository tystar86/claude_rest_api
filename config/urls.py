from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/", include("blog.api_urls")),
    path("", include("blog.urls")),
    path("", RedirectView.as_view(url="/dashboard/", permanent=False)),
]
