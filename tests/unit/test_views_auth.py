"""Unit tests for authentication API endpoints."""

import pytest
from django.contrib.auth.models import User
from rest_framework import status


# ── CSRF ───────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCsrfView:
    """Tests for GET /api/auth/csrf/."""

    def test_returns_200_and_csrf_token(self, api_client):
        """Anonymous requests receive a CSRF token in the response body."""
        resp = api_client.get("/api/auth/csrf/")
        assert resp.status_code == status.HTTP_200_OK
        assert "csrfToken" in resp.data
        assert resp.data["csrfToken"]


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
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["username"] == "newuser"

    def test_creates_user_in_database(self, api_client):
        """Registration persists the new user to the database."""
        api_client.post(
            "/api/auth/register/",
            {"email": "db@example.com", "username": "dbuser", "password": "dbpass123"},
            format="json",
        )
        assert User.objects.filter(username="dbuser").exists()

    def test_missing_fields_returns_400(self, api_client):
        """Omitting required fields returns 400."""
        resp = api_client.post(
            "/api/auth/register/",
            {"email": "incomplete@example.com"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_email_returns_400(self, api_client, user):
        """Registering with an already-used email returns 400."""
        resp = api_client.post(
            "/api/auth/register/",
            {"email": "test@example.com", "username": "other", "password": "pass1234"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["detail"] == "Registration failed."

    def test_duplicate_username_returns_400(self, api_client, user):
        """Registering with an already-taken username returns 400."""
        resp = api_client.post(
            "/api/auth/register/",
            {
                "email": "different@example.com",
                "username": "testuser",
                "password": "pass1234",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["detail"] == "Registration failed."

    def test_duplicate_registration_error_is_generic(self, api_client, user):
        """Duplicate registrations always return the same generic message regardless of which field collides."""
        resp_email = api_client.post(
            "/api/auth/register/",
            {"email": "test@example.com", "username": "other", "password": "pass1234"},
            format="json",
        )
        resp_username = api_client.post(
            "/api/auth/register/",
            {
                "email": "different@example.com",
                "username": "testuser",
                "password": "pass1234",
            },
            format="json",
        )
        assert resp_email.status_code == status.HTTP_400_BAD_REQUEST
        assert resp_username.status_code == status.HTTP_400_BAD_REQUEST
        assert (
            resp_email.data["detail"]
            == resp_username.data["detail"]
            == "Registration failed."
        )


# ── Login ──────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestLoginView:
    """Tests for POST /api/auth/login/."""

    def test_successful_login_returns_200(self, api_client, user):
        """Valid credentials authenticate the user and return 200 with user data."""
        resp = api_client.post(
            "/api/auth/login/",
            {"email": "test@example.com", "password": "testpass123"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["username"] == "testuser"

    def test_wrong_password_returns_400(self, api_client, user):
        """An incorrect password returns 400 with an 'Invalid credentials' message."""
        resp = api_client.post(
            "/api/auth/login/",
            {"email": "test@example.com", "password": "wrongpass"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["detail"] == "Invalid credentials."

    def test_unknown_email_returns_400(self, api_client):
        """A non-existent email returns 400."""
        resp = api_client.post(
            "/api/auth/login/",
            {"email": "nobody@example.com", "password": "pass"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_email_in_db_returns_400(self, api_client, user):
        """MultipleObjectsReturned when two DB rows share an email is treated as auth failure."""
        other = User.objects.create_user(
            username="other", email="other@example.com", password="otherpass123"
        )
        # Force both users to share the same email, bypassing the unique constraint
        User.objects.filter(pk=other.pk).update(email="test@example.com")

        resp = api_client.post(
            "/api/auth/login/",
            {"email": "test@example.com", "password": "testpass123"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["detail"] == "Invalid credentials."


# ── Logout ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestLogoutView:
    """Tests for POST /api/auth/logout/."""

    def test_authenticated_logout_returns_200(self, auth_client):
        """An authenticated user can log out successfully."""
        resp = auth_client.post("/api/auth/logout/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["detail"] == "Logged out."

    def test_unauthenticated_logout_returns_403(self, api_client):
        """An unauthenticated request to logout is rejected."""
        resp = api_client.post("/api/auth/logout/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ── Current User ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCurrentUserView:
    """Tests for GET /api/auth/user/."""

    def test_authenticated_returns_user_data(self, auth_client, user):
        """Authenticated users receive their own serialized data."""
        resp = auth_client.get("/api/auth/user/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["username"] == "testuser"

    def test_unauthenticated_returns_401(self, api_client):
        """Unauthenticated requests are rejected with 401."""
        resp = api_client.get("/api/auth/user/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ── Update Profile ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestUpdateProfileView:
    """Tests for PATCH /api/auth/profile/."""

    def test_change_username_succeeds(self, auth_client):
        """Providing a new unique username updates it successfully."""
        resp = auth_client.patch(
            "/api/auth/profile/", {"username": "newname"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["username"] == "newname"

    def test_change_password_succeeds(self, auth_client):
        """Providing correct current password allows password change."""
        resp = auth_client.patch(
            "/api/auth/profile/",
            {"current_password": "testpass123", "new_password": "newpassword456"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_wrong_current_password_returns_400(self, auth_client):
        """An incorrect current password is rejected with a field error."""
        resp = auth_client.patch(
            "/api/auth/profile/",
            {"current_password": "wrongpass", "new_password": "newpassword456"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "current_password" in resp.data

    def test_new_password_too_short_returns_400(self, auth_client):
        """A new password shorter than 8 characters is rejected."""
        resp = auth_client.patch(
            "/api/auth/profile/",
            {"current_password": "testpass123", "new_password": "short"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "new_password" in resp.data

    def test_taken_username_returns_400(self, auth_client, db):
        """Attempting to take another user's username is rejected."""
        User.objects.create_user(username="taken", email="taken@x.com", password="p")
        resp = auth_client.patch(
            "/api/auth/profile/", {"username": "taken"}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "username" in resp.data

    def test_empty_username_returns_400(self, auth_client):
        """Submitting an empty string for username is rejected."""
        resp = auth_client.patch("/api/auth/profile/", {"username": ""}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
