"""Ninja API package: routers, app instance, and shared API constants."""

# Error detail string for Ninja AuthenticationError and manual 401 JSON bodies.
# Defined before submodule imports so `from blog.api import …` / relative imports
# work without circular import (routers are loaded from this package).
AUTHENTICATION_REQUIRED_DETAIL = "Authentication credentials were not provided."

from django.http import JsonResponse
from ninja import NinjaAPI
from ninja.errors import AuthenticationError

from .auth import router as auth_router
from .data import router as data_router

api = NinjaAPI(
    title="claude_rest_api",
    version="0.1.0",
    urls_namespace="blog_api",
)


@api.exception_handler(AuthenticationError)
def authentication_error(request, exc):
    return JsonResponse({"detail": AUTHENTICATION_REQUIRED_DETAIL}, status=403)


api.add_router("/auth/", auth_router)
api.add_router("/", data_router)
