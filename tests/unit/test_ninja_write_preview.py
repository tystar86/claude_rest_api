"""Preview tests for write-oriented Ninja migration routes."""

import json
from contextlib import contextmanager

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import Client, override_settings

from blog.api import preview_write_api
from blog.api.write import throttling as write_throttling
from blog.models import Post


@contextmanager
def _temporary_throttle_rate(throttle, rate: str):
    original_rate = throttle.rate
    original_num_requests = throttle.num_requests
    original_duration = throttle.duration
    throttle.rate = rate
    throttle.num_requests, throttle.duration = throttle.parse_rate(rate)
    try:
        yield
    finally:
        throttle.rate = original_rate
        throttle.num_requests = original_num_requests
        throttle.duration = original_duration


@pytest.mark.django_db
class TestNinjaWritePreview:
    """Smoke coverage for the preview write Ninja surface."""

    def test_openapi_json_is_available(self, api_client):
        resp = api_client.get("/api/_ninja/write/openapi.json")
        assert resp.status_code == 200
        assert json.loads(resp.content)["openapi"] == "3.1.0"

    def test_posts_create_preserves_auth_requirements(self, user):
        anon_client = Client()
        auth_client = Client()
        auth_client.force_login(user)

        anon = anon_client.post(
            "/api/_ninja/write/posts/",
            {"title": "Preview Post", "body": "body"},
            content_type="application/json",
        )
        authed = auth_client.post(
            "/api/_ninja/write/posts/",
            {"title": "Preview Post", "body": "body"},
            content_type="application/json",
        )

        assert anon.status_code == 401
        assert authed.status_code == 201
        assert authed.json()["title"] == "Preview Post"

    def test_tag_create_respects_moderator_permissions(self, user, moderator):
        user_client = Client()
        user_client.force_login(user)
        mod_client = Client()
        mod_client.force_login(moderator)

        user_resp = user_client.post(
            "/api/_ninja/write/tags/",
            {"name": "not-allowed"},
            content_type="application/json",
        )
        mod_resp = mod_client.post(
            "/api/_ninja/write/tags/",
            {"name": "allowed-tag"},
            content_type="application/json",
        )

        assert user_resp.status_code == 403
        assert mod_resp.status_code == 201

    def test_comment_vote_route_matches_existing_behavior(self, user, comment):
        anon_client = Client()
        auth_client = Client()
        auth_client.force_login(user)

        anon = anon_client.post(
            f"/api/_ninja/write/comments/{comment.id}/vote/",
            {"vote": "like"},
            content_type="application/json",
        )
        authed = auth_client.post(
            f"/api/_ninja/write/comments/{comment.id}/vote/",
            {"vote": "like"},
            content_type="application/json",
        )

        assert anon.status_code == 401
        assert authed.status_code == 200
        assert authed.json()["likes"] == 1

    def test_comment_create_rejects_invalid_parent_id(self, user, post):
        client = Client()
        client.force_login(user)
        resp = client.post(
            f"/api/_ninja/write/posts/{post.slug}/comments/",
            {"body": "reply", "parent_id": {"bad": "value"}},
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid parent_id."

    def test_public_delete_route_dispatches_to_delete_handler(self, user, post):
        anon_client = Client()
        auth_client = Client()
        auth_client.force_login(user)
        post.author = user
        post.save(update_fields=["author"])

        anon_resp = anon_client.delete(f"/api/posts/{post.slug}/")
        auth_resp = auth_client.delete(f"/api/posts/{post.slug}/")

        assert anon_resp.status_code == 401
        assert auth_resp.status_code == 204
        assert Post.objects.filter(pk=post.pk).exists() is False

    def test_head_request_falls_back_to_get_dispatch(self, api_client):
        head_resp = api_client.head("/api/posts/")
        get_resp = api_client.get("/api/posts/")
        assert head_resp.status_code == 200
        assert get_resp.status_code == 200

    def test_login_route_rate_limits_with_low_scope_rate(self):
        assert preview_write_api.urls_namespace == "blog_ninja_write_preview"
        base_rates = dict(settings.API_THROTTLE_RATES)
        low_rates = {
            **base_rates,
            "login": "1/min",
            "resend_verification": "1/min",
        }

        with override_settings(
            API_THROTTLE_RATES=low_rates,
            NINJA_DEFAULT_THROTTLE_RATES=low_rates,
            CACHES={
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                    "LOCATION": "test-ninja-write-preview-login-throttle",
                }
            },
        ):
            assert settings.API_THROTTLE_RATES["login"] == "1/min"
            cache.clear()
            throttle = write_throttling.WRITE_LOGIN_THROTTLES[0]
            with _temporary_throttle_rate(
                throttle, settings.API_THROTTLE_RATES["login"]
            ):
                client = Client()
                first = client.post(
                    "/api/_ninja/write/auth/login/",
                    {"email": "missing@example.com", "password": "wrongpass"},
                    content_type="application/json",
                )
                second = client.post(
                    "/api/_ninja/write/auth/login/",
                    {"email": "missing@example.com", "password": "wrongpass"},
                    content_type="application/json",
                )
            cache.clear()

        assert first.status_code == 400
        assert second.status_code == 429

    def test_resend_route_rate_limits_with_low_scope_rate(self, user):
        assert preview_write_api.urls_namespace == "blog_ninja_write_preview"
        base_rates = dict(settings.API_THROTTLE_RATES)
        low_rates = {
            **base_rates,
            "login": "1/min",
            "resend_verification": "1/min",
        }

        with override_settings(
            API_THROTTLE_RATES=low_rates,
            NINJA_DEFAULT_THROTTLE_RATES=low_rates,
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            CACHES={
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                    "LOCATION": "test-ninja-write-preview-resend-throttle",
                }
            },
        ):
            assert settings.API_THROTTLE_RATES["resend_verification"] == "1/min"
            cache.clear()
            throttle = write_throttling.WRITE_RESEND_VERIFICATION_THROTTLES[0]
            with _temporary_throttle_rate(
                throttle,
                settings.API_THROTTLE_RATES["resend_verification"],
            ):
                client = Client()
                client.force_login(user)
                first = client.post("/api/_ninja/write/auth/resend-verification/")
                second = client.post("/api/_ninja/write/auth/resend-verification/")
            cache.clear()

        assert first.status_code == 200
        assert second.status_code == 429
