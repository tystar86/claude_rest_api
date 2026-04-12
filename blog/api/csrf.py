"""JSON-safe CSRF failure view and API middleware helpers."""

from django.http import JsonResponse


def _wants_json(request) -> bool:
    accept = request.META.get("HTTP_ACCEPT", "")
    return request.path.startswith("/api/") or "application/json" in accept


def csrf_failure_view(request, reason=""):
    if _wants_json(request):
        return JsonResponse(
            {"detail": "CSRF token missing or invalid."},
            status=403,
        )
    from django.views.csrf import csrf_failure as default_csrf_failure

    return default_csrf_failure(request, reason=reason)


class JsonMethodNotAllowedMiddleware:
    """Convert HTML 405 responses on /api/ paths to JSON."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            response.status_code == 405
            and request.path.startswith("/api/")
            and "application/json" not in response.get("Content-Type", "")
        ):
            allowed = response.get("Allow", "")
            json_response = JsonResponse(
                {"detail": "Method not allowed."},
                status=405,
            )
            if allowed:
                json_response["Allow"] = allowed
            return json_response
        return response
