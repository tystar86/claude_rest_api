"""Shared API utilities."""

import json

from django.http import HttpRequest, JsonResponse

from blog.utils import build_unique_slug

__all__ = ["build_unique_slug", "request_data_or_error"]


def request_data_or_error(request: HttpRequest) -> tuple[dict, JsonResponse | None]:
    """Parse JSON body as an object. Returns (data, None) or ({}, 400 JsonResponse).

    json.loads raises JSONDecodeError on invalid JSON; that type subclasses ValueError,
    so one except ValueError covers parse errors and non-object bodies.
    """
    raw_body = getattr(request, "body", b"") or b""
    if not raw_body:
        return {}, None
    try:
        data = json.loads(raw_body)
        if not isinstance(data, dict):
            raise ValueError
    except ValueError:
        return {}, JsonResponse({"detail": "Malformed JSON body."}, status=400)
    return data, None
