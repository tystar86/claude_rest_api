from ninja import NinjaAPI
from ninja.errors import AuthenticationError

from .auth import router as auth_router
from .auth.services import AUTHENTICATION_REQUIRED_DETAIL, json_compat_response
from .data import router as data_router

api = NinjaAPI(
    title="claude_rest_api",
    version="0.1.0",
    urls_namespace="blog_api",
)


@api.exception_handler(AuthenticationError)
def authentication_error(request, exc):
    return json_compat_response(
        {"detail": AUTHENTICATION_REQUIRED_DETAIL},
        status=403,
    )


api.add_router("/auth/", auth_router)
api.add_router("/", data_router)
