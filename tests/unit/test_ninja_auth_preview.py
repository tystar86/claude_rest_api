import pytest
from django.test import Client


@pytest.mark.django_db
class TestNinjaAuth:
    def test_csrf_returns_token_and_cookie(self, client):
        resp = client.get("/api/auth/csrf/")

        assert resp.status_code == 200
        assert resp.json()["csrfToken"]
        assert resp.cookies["csrftoken"].value

    def test_current_user_requires_authentication(self, client):
        resp = client.get("/api/auth/user/")

        assert resp.status_code == 403
        assert resp.json()["detail"] == "Authentication credentials were not provided."

    def test_current_user_returns_current_user_payload(self, client, user):
        client.force_login(user)

        resp = client.get("/api/auth/user/")

        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == user.username
        assert data["email"] == user.email
        assert data["profile"]["role"] == "user"
        assert data["can_manage_tags"] is False

    def test_logout_requires_authentication(self, client):
        resp = client.post("/api/auth/logout/")

        assert resp.status_code == 403
        assert resp.json()["detail"] == "Authentication credentials were not provided."

    def test_logout_succeeds_with_valid_csrf(self, user):
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)

        csrf_resp = client.get("/api/auth/csrf/")
        csrf_token = csrf_resp.cookies["csrftoken"].value

        resp = client.post(
            "/api/auth/logout/",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        assert resp.status_code == 200
        assert resp.json()["detail"] == "Logged out."

        after = client.get("/api/auth/user/")
        assert after.status_code == 403
