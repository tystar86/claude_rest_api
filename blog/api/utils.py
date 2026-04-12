"""Shared API utilities."""

import json

from django.http import HttpRequest

from .auth.services import json_compat_response


def request_data(request: HttpRequest) -> dict:
    raw_body = getattr(request, "body", b"") or b""
    if not raw_body:
        return {}
    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise ValueError("Malformed JSON body.") from exc
    if isinstance(data, dict):
        return data
    raise ValueError("JSON body must be an object.")


def request_data_or_error(request: HttpRequest):
    try:
        return request_data(request), None
    except ValueError as exc:
        return {}, json_compat_response({"detail": str(exc)}, status=400)
