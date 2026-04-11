from django.urls import URLPattern
from ninja.errors import AuthenticationError
from ninja import NinjaAPI

from .auth import router as auth_router
from .auth.services import AUTHENTICATION_REQUIRED_DETAIL, json_compat_response
from .read import router as read_router


def _add_auth_handlers(api: NinjaAPI) -> None:
    @api.exception_handler(AuthenticationError)
    def authentication_error(request, exc):
        return json_compat_response(
            {"detail": AUTHENTICATION_REQUIRED_DETAIL},
            status=403,
        )


public_auth_api = NinjaAPI(
    title="claude_rest_api auth",
    version="0.1.0",
    description="Public auth surface served by Django Ninja during the migration.",
    urls_namespace="blog_ninja_auth_public",
    docs_url=None,
    openapi_url=None,
)

preview_auth_api = NinjaAPI(
    title="claude_rest_api auth preview",
    version="0.1.0",
    description="Preview Ninja auth surface for the DRF-to-Ninja migration.",
    urls_namespace="blog_ninja_auth_preview",
    docs_url=None,
    openapi_url="/openapi.json",
)

_add_auth_handlers(public_auth_api)
_add_auth_handlers(preview_auth_api)

public_auth_api.add_router("/", auth_router)
preview_auth_api.add_router("/", auth_router)

public_read_api = NinjaAPI(
    title="claude_rest_api read API",
    version="0.1.0",
    description="Public read-only surface served by Django Ninja during the migration.",
    urls_namespace="blog_ninja_read_public",
    docs_url=None,
    openapi_url=None,
)

preview_read_api = NinjaAPI(
    title="claude_rest_api read API preview",
    version="0.1.0",
    description="Preview Ninja read-only surface for the DRF-to-Ninja migration.",
    urls_namespace="blog_ninja_read_preview",
    docs_url=None,
    openapi_url="/openapi.json",
)

public_read_api.add_router("/", read_router)
preview_read_api.add_router("/", read_router)


def _build_callback_map(api: NinjaAPI) -> dict[str, callable]:
    return {
        pattern.name: pattern.callback
        for pattern in api.urls[0]
        if isinstance(pattern, URLPattern)
    }


public_read_callbacks = _build_callback_map(public_read_api)
