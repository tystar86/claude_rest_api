from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/", include("blog.api_urls")),
    # path("silk/", include("silk.urls", namespace="silk")), # Uncomment to enable django-silk (dev only)
]
