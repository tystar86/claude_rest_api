"""Ninja API package: routers and app instance."""

from django.http import JsonResponse
from ninja import NinjaAPI
from ninja.errors import AuthenticationError

from .auth import router as auth_router
from .constants import AUTHENTICATION_REQUIRED_DETAIL
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
