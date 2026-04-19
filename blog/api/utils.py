"""Shared API utilities."""

import json

from django.http import HttpRequest, JsonResponse
from django.utils.text import slugify


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


def build_unique_slug(model_cls, source_text, instance_id=None, max_length=None):
    if max_length is None:
        max_length = model_cls._meta.get_field("slug").max_length
    base = slugify(source_text or "").strip("-")[:max_length] or "item"
    candidate = base
    n = 2
    while True:
        qs = model_cls.objects.filter(slug=candidate)
        if instance_id is not None:
            qs = qs.exclude(id=instance_id)
        if not qs.exists():
            return candidate
        suffix = f"-{n}"
        candidate = f"{base[: max_length - len(suffix)]}{suffix}"
        n += 1
