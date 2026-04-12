"""Preview tests for write-oriented Ninja migration routes."""

import json

import pytest
from django.conf import settings
from rest_framework import status
from rest_framework.test import APIClient

from blog.api import preview_write_api
from blog.api.write.throttling import (
    WriteLoginThrottle,
    WriteResendVerificationThrottle,
)


@pytest.mark.django_db
class TestNinjaWritePreview:
    """Smoke coverage for the preview write Ninja surface."""

    def test_openapi_json_is_available(self, api_client):
        resp = api_client.get("/api/_ninja/write/openapi.json")
        assert resp.status_code == status.HTTP_200_OK
        assert json.loads(resp.content)["openapi"] == "3.1.0"

    def test_posts_create_preserves_auth_requirements(self, user):
        anon_client = APIClient()
        auth_client = APIClient()
        auth_client.force_authenticate(user=user)

        anon = anon_client.post(
            "/api/_ninja/write/posts/",
            {"title": "Preview Post", "body": "body"},
            format="json",
        )
        authed = auth_client.post(
            "/api/_ninja/write/posts/",
            {"title": "Preview Post", "body": "body"},
            format="json",
        )

        assert anon.status_code == status.HTTP_401_UNAUTHORIZED
        assert authed.status_code == status.HTTP_201_CREATED
        assert authed.data["title"] == "Preview Post"

    def test_tag_create_respects_moderator_permissions(self, user, moderator):
        user_client = APIClient()
        user_client.force_authenticate(user=user)
        mod_client = APIClient()
        mod_client.force_authenticate(user=moderator)

        user_resp = user_client.post(
            "/api/_ninja/write/tags/",
            {"name": "not-allowed"},
            format="json",
        )
        mod_resp = mod_client.post(
            "/api/_ninja/write/tags/",
            {"name": "allowed-tag"},
            format="json",
        )

        assert user_resp.status_code == status.HTTP_403_FORBIDDEN
        assert mod_resp.status_code == status.HTTP_201_CREATED

    def test_comment_vote_route_matches_existing_behavior(self, user, comment):
        anon_client = APIClient()
        auth_client = APIClient()
        auth_client.force_authenticate(user=user)

        anon = anon_client.post(
            f"/api/_ninja/write/comments/{comment.id}/vote/",
            {"vote": "like"},
            format="json",
        )
        authed = auth_client.post(
            f"/api/_ninja/write/comments/{comment.id}/vote/",
            {"vote": "like"},
            format="json",
        )

        assert anon.status_code == status.HTTP_403_FORBIDDEN
        assert authed.status_code == status.HTTP_200_OK
        assert authed.data["likes"] == 1

    def test_public_delete_route_dispatches_to_delete_handler(self, user, post):
        anon_client = APIClient()
        auth_client = APIClient()
        auth_client.force_authenticate(user=user)

        anon_resp = anon_client.delete(f"/api/posts/{post.slug}/")
        auth_resp = auth_client.delete(f"/api/posts/{post.slug}/")

        assert anon_resp.status_code != status.HTTP_404_NOT_FOUND
        assert auth_resp.status_code != status.HTTP_404_NOT_FOUND

    def test_login_route_uses_login_scope_throttle(self):
        bound_routers = preview_write_api._get_bound_routers()
        for bound_router in bound_routers:
            for _, path_view in bound_router.path_operations.items():
                for operation in path_view.operations:
                    if operation.view_func.__name__ != "login":
                        continue
                    assert any(
                        isinstance(throttle, WriteLoginThrottle)
                        for throttle in operation.throttle_objects
                    )
                    assert (
                        WriteLoginThrottle().rate
                        == settings.API_THROTTLE_RATES["login"]
                    )
                    return
        raise AssertionError("Could not find login operation in preview_write_api")

    def test_resend_route_uses_resend_verification_scope_throttle(self):
        bound_routers = preview_write_api._get_bound_routers()
        for bound_router in bound_routers:
            for _, path_view in bound_router.path_operations.items():
                for operation in path_view.operations:
                    if operation.view_func.__name__ != "resend_verification":
                        continue
                    assert len(operation.throttle_objects) == 1
                    assert isinstance(
                        operation.throttle_objects[0], WriteResendVerificationThrottle
                    )
                    assert (
                        WriteResendVerificationThrottle().rate
                        == settings.API_THROTTLE_RATES["resend_verification"]
                    )
                    return
        raise AssertionError(
            "Could not find resend_verification operation in preview_write_api"
        )
