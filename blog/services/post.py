"""Create and update posts (validation + persistence for Ninja routes)."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User
from django.utils import timezone

from blog.models import Post, Tag
from blog.utils import build_unique_slug


def _clean_tag_ids(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, list):
        return "Not a valid list of integers."
    for x in value:
        if not isinstance(x, int):
            return "Not a valid list of integers."
    existing = set(Tag.objects.filter(id__in=value).values_list("id", flat=True))
    missing = sorted(set(value) - existing)
    if missing:
        return f"Tag IDs not found: {missing}"
    return None


def _validate_create_payload(data: dict) -> tuple[dict[str, Any] | None, dict[str, list[str]]]:
    errors: dict[str, list[str]] = {}
    title = data.get("title")
    body = data.get("body")
    if not isinstance(title, str):
        errors.setdefault("title", []).append("Not a valid string.")
    elif not title.strip():
        errors.setdefault("title", []).append("This field is required.")
    if not isinstance(body, str):
        errors.setdefault("body", []).append("Not a valid string.")
    elif not body.strip():
        errors.setdefault("body", []).append("This field is required.")
    excerpt = data.get("excerpt", "")
    if excerpt is not None and not isinstance(excerpt, str):
        errors.setdefault("excerpt", []).append("Not a valid string.")
    status = data.get("status", Post.Status.DRAFT)
    if status is not None and status not in (Post.Status.DRAFT, Post.Status.PUBLISHED):
        errors.setdefault("status", []).append(f'"{status}" is not a valid choice.')
    if "tag_ids" in data:
        tag_err = _clean_tag_ids(data["tag_ids"])
        if tag_err:
            errors.setdefault("tag_ids", []).append(tag_err)
    if errors:
        return None, errors
    validated: dict[str, Any] = {
        "title": title.strip(),
        "body": body.strip(),
        "excerpt": (excerpt or "") if isinstance(excerpt, str) else "",
        "status": status,
    }
    if "tag_ids" in data:
        validated["tag_ids"] = data["tag_ids"]
    return validated, {}


def _validate_update_payload(data: dict) -> tuple[dict[str, Any] | None, dict[str, list[str]]]:
    errors: dict[str, list[str]] = {}
    validated: dict[str, Any] = {}
    if "title" in data:
        t = data["title"]
        if not isinstance(t, str) or not t.strip():
            errors.setdefault("title", []).append("This field may not be blank.")
        else:
            validated["title"] = t.strip()
    if "body" in data:
        b = data["body"]
        if not isinstance(b, str) or not b.strip():
            errors.setdefault("body", []).append("This field may not be blank.")
        else:
            validated["body"] = b.strip()
    if "excerpt" in data:
        ex = data["excerpt"]
        if ex is not None and not isinstance(ex, str):
            errors.setdefault("excerpt", []).append("Not a valid string.")
        else:
            validated["excerpt"] = ex if isinstance(ex, str) else ""
    if "status" in data:
        st = data["status"]
        if st is not None and st not in (Post.Status.DRAFT, Post.Status.PUBLISHED):
            errors.setdefault("status", []).append(f'"{st}" is not a valid choice.')
        else:
            validated["status"] = st
    if "tag_ids" in data:
        tag_err = _clean_tag_ids(data["tag_ids"])
        if tag_err:
            errors.setdefault("tag_ids", []).append(tag_err)
        else:
            validated["tag_ids"] = data["tag_ids"]
    if errors:
        return None, errors
    return validated, {}


class PostService:
    """Validate JSON payloads and persist ``Post`` rows for the Ninja API."""

    @staticmethod
    def create(*, author: User, data: Any) -> tuple[Post | None, dict[str, list[str]]]:
        if not isinstance(data, dict):
            return None, {"non_field_errors": ["Invalid payload."]}
        validated, errors = _validate_create_payload(data)
        if errors:
            return None, errors
        vd = dict(validated)
        tag_ids = vd.pop("tag_ids", []) or []
        status_value = vd.get("status", Post.Status.DRAFT)
        post = Post.objects.create(
            title=vd["title"],
            slug=build_unique_slug(Post, vd["title"]),
            author=author,
            body=vd["body"],
            excerpt=vd.get("excerpt", ""),
            status=status_value,
            published_at=(timezone.now() if status_value == Post.Status.PUBLISHED else None),
        )
        if tag_ids:
            post.tags.set(Tag.objects.filter(id__in=tag_ids))
        return post, {}

    @staticmethod
    def update(*, instance: Post, data: Any) -> tuple[Post | None, dict[str, list[str]]]:
        if not isinstance(data, dict):
            return None, {"non_field_errors": ["Invalid payload."]}
        validated, errors = _validate_update_payload(data)
        if errors:
            return None, errors
        vd = validated
        if "title" in vd:
            instance.title = vd["title"]
            instance.slug = build_unique_slug(Post, instance.title, instance_id=instance.id)
        if "body" in vd:
            instance.body = vd["body"]
        if "excerpt" in vd:
            instance.excerpt = vd["excerpt"]
        if (status_value := vd.get("status")) is not None:
            instance.status = status_value
            if status_value == Post.Status.PUBLISHED:
                instance.published_at = instance.published_at or timezone.now()
            else:
                instance.published_at = None
        instance.save()
        if "tag_ids" in vd:
            tids = vd["tag_ids"]
            if tids is not None:
                instance.tags.set(Tag.objects.filter(id__in=tids))
        return instance, {}
