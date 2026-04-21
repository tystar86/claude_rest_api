"""Unit tests for authentication API endpoints."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client

User = get_user_model()


# ── CSRF ───────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCsrfView:
    """Tests for GET /api/auth/csrf/."""

    def test_returns_200_and_csrf_token(self, api_client):
        """Anonymous requests receive a CSRF token in the response body."""
        resp = api_client.get("/api/auth/csrf/")
        assert resp.status_code == 200
        assert "csrfToken" in resp.json()
        assert resp.json()["csrfToken"]


# ── Register ───────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestRegisterView:
    """Tests for POST /api/auth/register/."""

    def test_successful_registration_returns_201(self, api_client):
        """Valid credentials create a user and return 201 with user data."""
        resp = api_client.post(
            "/api/auth/register/",
            {
                "email": "new@example.com",
                "username": "newuser",
                "password": "newpass123",
            },
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["username"] == "newuser"

    def test_creates_user_in_database(self, api_client):
        """Registration persists the new user to the database."""
        api_client.post(
            "/api/auth/register/",
            {"email": "db@example.com", "username": "dbuser", "password": "dbpass123"},
            content_type="application/json",
        )
        assert User.objects.filter(username="dbuser").exists()

    def test_registration_normalizes_email_before_saving(self, api_client):
        """Registration persists email in canonical lowercase/trimmed form."""
        api_client.post(
            "/api/auth/register/",
            {
                "email": "  MixedCase@Example.COM  ",
                "username": "mixedcaseuser",
                "password": "newpass123",
            },
            content_type="application/json",
        )
        created_user = User.objects.get(username="mixedcaseuser")
        assert created_user.email == "mixedcase@example.com"

    def test_missing_fields_returns_400(self, api_client):
        """Omitting required fields returns 400."""
        resp = api_client.post(
            "/api/auth/register/",
            {"email": "incomplete@example.com"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_non_string_required_fields_return_400(self, api_client):
        """Non-string required fields are rejected with the standard missing-fields detail."""
        resp = api_client.post(
            "/api/auth/register/",
            {"email": ["bad"], "username": {"bad": "type"}, "password": 123},
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "email, username and password are required."

    def test_duplicate_email_returns_400(self, api_client, user):
        """Registering with an already-used email returns 400."""
        resp = api_client.post(
            "/api/auth/register/",
            {"email": "test@example.com", "username": "other", "password": "pass1234"},
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Registration failed."

    def test_duplicate_username_returns_400(self, api_client, user):
        """Registering with an already-taken username returns 400."""
        resp = api_client.post(
            "/api/auth/register/",
            {
                "email": "different@example.com",
                "username": "testuser",
                "password": "pass1234",
            },
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Registration failed."

    def test_duplicate_registration_error_is_generic(self, api_client, user):
        """Duplicate registrations always return the same generic message regardless of which field collides."""
        resp_email = api_client.post(
            "/api/auth/register/",
            {"email": "test@example.com", "username": "other", "password": "pass1234"},
            content_type="application/json",
        )
        resp_username = api_client.post(
            "/api/auth/register/",
            {
                "email": "different@example.com",
                "username": "testuser",
                "password": "pass1234",
            },
            content_type="application/json",
        )
        assert resp_email.status_code == 400
        assert resp_username.status_code == 400
        assert (
            resp_email.json()["detail"] == resp_username.json()["detail"] == "Registration failed."
        )

    def test_weak_password_returns_400(self, api_client):
        """Registration rejects passwords that fail Django validators."""
        resp = api_client.post(
            "/api/auth/register/",
            {
                "email": "weak@example.com",
                "username": "weakuser",
                "password": "123",
            },
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "password" in resp.json()
        assert resp.json()["password"]


# ── Login ──────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestLoginView:
    """Tests for POST /api/auth/login/."""

    def test_successful_login_returns_200(self, api_client, user):
        """Valid credentials authenticate the user and return 200 with user data."""
        resp = api_client.post(
            "/api/auth/login/",
            {"email": "test@example.com", "password": "testpass123"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "testuser"

    def test_wrong_password_returns_400(self, api_client, user):
        """An incorrect password returns 400 with an 'Invalid credentials' message."""
        resp = api_client.post(
            "/api/auth/login/",
            {"email": "test@example.com", "password": "wrongpass"},
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid credentials."

    def test_unknown_email_returns_400(self, api_client):
        """A non-existent email returns 400."""
        resp = api_client.post(
            "/api/auth/login/",
            {"email": "nobody@example.com", "password": "pass"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_non_string_credentials_return_400(self, api_client):
        """NoSQL-style dict payloads must be rejected with 400, not cause a 500."""
        resp = api_client.post(
            "/api/auth/login/",
            {"email": {"$ne": ""}, "password": {"$ne": ""}},
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid credentials."

    def test_get_login_returns_json_405(self, api_client):
        """Unsupported methods return a JSON 405 payload with Allow header."""
        resp = api_client.get("/api/auth/login/")
        assert resp.status_code == 405
        assert resp.json()["detail"] == "Method not allowed."
        assert "POST" in resp.headers.get("Allow", "")

    def test_duplicate_email_lookup_returns_400(self, api_client, monkeypatch):
        """MultipleObjectsReturned during email lookup is treated as auth failure."""

        def raise_multiple(*args, **kwargs):
            raise User.MultipleObjectsReturned

        monkeypatch.setattr(User.objects, "get", raise_multiple)
        resp = api_client.post(
            "/api/auth/login/",
            {"email": "test@example.com", "password": "testpass123"},
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid credentials."

    def test_login_normalizes_email_before_lookup(self, api_client, user):
        """Login accepts equivalent emails with surrounding whitespace/case differences."""
        resp = api_client.post(
            "/api/auth/login/",
            {"email": "  TEST@EXAMPLE.COM  ", "password": "testpass123"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "testuser"


# ── Logout ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestLogoutView:
    """Tests for POST /api/auth/logout/."""

    def test_authenticated_logout_returns_200(self, auth_client):
        """An authenticated user can log out successfully."""
        resp = auth_client.post("/api/auth/logout/")
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Logged out."

    def test_unauthenticated_logout_returns_403(self, api_client):
        """An unauthenticated request to logout is rejected."""
        resp = api_client.post("/api/auth/logout/")
        assert resp.status_code == 403


# ── Current User ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCurrentUserView:
    """Tests for GET /api/auth/user/."""

    def test_authenticated_returns_user_data(self, auth_client, user):
        """Authenticated users receive their own serialized data."""
        resp = auth_client.get("/api/auth/user/")
        assert resp.status_code == 200
        assert resp.json()["username"] == "testuser"

    def test_unauthenticated_returns_403(self, api_client):
        """Unauthenticated requests are rejected with 403."""
        resp = api_client.get("/api/auth/user/")
        assert resp.status_code == 403


# ── Update Profile ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestUpdateProfileView:
    """Tests for PATCH /api/auth/profile/."""

    def test_change_username_succeeds(self, auth_client):
        """Providing a new unique username updates it successfully."""
        resp = auth_client.patch(
            "/api/auth/profile/",
            {"username": "newname"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "newname"

    def test_change_password_succeeds(self, auth_client):
        """Providing correct current password allows password change."""
        resp = auth_client.patch(
            "/api/auth/profile/",
            {"current_password": "testpass123", "new_password": "newpassword456"},
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_wrong_current_password_returns_400(self, auth_client):
        """An incorrect current password is rejected with a field error."""
        resp = auth_client.patch(
            "/api/auth/profile/",
            {"current_password": "wrongpass", "new_password": "newpassword456"},
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "current_password" in resp.json()

    def test_new_password_too_short_returns_400(self, auth_client):
        """A new password shorter than 8 characters is rejected."""
        resp = auth_client.patch(
            "/api/auth/profile/",
            {"current_password": "testpass123", "new_password": "short"},
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "new_password" in resp.json()

    def test_taken_username_returns_400(self, auth_client, db):
        """Attempting to take another user's username is rejected."""
        User.objects.create_user(username="taken", email="taken@x.com", password="p")
        resp = auth_client.patch(
            "/api/auth/profile/", {"username": "taken"}, content_type="application/json"
        )
        assert resp.status_code == 400
        assert "username" in resp.json()

    def test_username_integrity_error_on_save_returns_400(self, auth_client):
        """A username unique violation at save time maps to the same 400 as the pre-check."""
        with patch.object(User, "save", side_effect=IntegrityError()):
            resp = auth_client.patch(
                "/api/auth/profile/",
                {"username": "unusedunique99"},
                content_type="application/json",
            )
        assert resp.status_code == 400
        assert resp.json()["username"] == "Username already taken."

    def test_empty_username_returns_400(self, auth_client):
        """Submitting an empty string for username is rejected."""
        resp = auth_client.patch(
            "/api/auth/profile/", {"username": ""}, content_type="application/json"
        )
        assert resp.status_code == 400

    def test_non_string_profile_fields_return_400(self, auth_client):
        """Non-string profile update fields return explicit validation errors."""
        resp = auth_client.patch(
            "/api/auth/profile/",
            {
                "username": {"$ne": ""},
                "current_password": {"$ne": ""},
                "new_password": ["bad"],
            },
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.json()["username"] == "Username must be a string."
        assert resp.json()["new_password"] == "Password must be a string."


# ── User profile signal + session auth ─────────────────────────────────────────


@pytest.mark.django_db
class TestUserProfileAndSessionAuth:
    """Regression tests formerly grouped with OAuth-specific cases."""

    def test_create_user_is_persisted(self, db):
        """Saving a new CustomUser persists it to the database."""
        u = User.objects.create_user(
            username="prof_user",
            email="prof@example.com",
            password="pass12345",
        )
        assert User.objects.filter(pk=u.pk).exists()

    def test_force_login_user_can_access_current_user_endpoint(self, db):
        """An authenticated user can read GET /api/auth/user/."""
        u = User.objects.create_user(
            username="api_user",
            email="api@example.com",
            password="pass12345",
        )

        client = Client()
        client.force_login(u)
        resp = client.get("/api/auth/user/")
        assert resp.status_code == 200
        assert resp.json()["email"] == "api@example.com"

    def test_unauthenticated_cannot_access_user_endpoint(self, db):
        """GET /api/auth/user/ without a session returns 403."""
        client = Client()
        resp = client.get("/api/auth/user/")
        assert resp.status_code == 403
