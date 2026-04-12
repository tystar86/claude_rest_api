"""Unit tests for authentication API endpoints."""

import io
import smtplib
from unittest.mock import patch

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.db import connection
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

GENERIC_RESEND_DETAIL = "Verification email sent. Please check your inbox."


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

    def test_registration_normalizes_email_before_saving(self, api_client):
        """Registration persists email in canonical lowercase/trimmed form."""
        api_client.post(
            "/api/auth/register/",
            {
                "email": "  MixedCase@Example.COM  ",
                "username": "mixedcaseuser",
                "password": "newpass123",
            },
            format="json",
        )
        created_user = User.objects.get(username="mixedcaseuser")
        assert created_user.email == "mixedcase@example.com"

    def test_missing_fields_returns_400(self, api_client):
        """Omitting required fields returns 400."""
        resp = api_client.post(
            "/api/auth/register/",
            {"email": "incomplete@example.com"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_string_required_fields_return_400(self, api_client):
        """Non-string required fields are rejected with the standard missing-fields detail."""
        resp = api_client.post(
            "/api/auth/register/",
            {"email": ["bad"], "username": {"bad": "type"}, "password": 123},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["detail"] == "email, username and password are required."

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

    def test_weak_password_returns_400(self, api_client):
        """Registration rejects passwords that fail Django validators."""
        resp = api_client.post(
            "/api/auth/register/",
            {
                "email": "weak@example.com",
                "username": "weakuser",
                "password": "123",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in resp.data
        assert resp.data["password"]


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

    def test_non_string_credentials_return_400(self, api_client):
        """NoSQL-style dict payloads must be rejected with 400, not cause a 500."""
        resp = api_client.post(
            "/api/auth/login/",
            {"email": {"$ne": ""}, "password": {"$ne": ""}},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["detail"] == "Invalid credentials."

    def test_get_login_returns_json_405(self, api_client):
        """Unsupported methods return a JSON 405 payload with Allow header."""
        resp = api_client.get("/api/auth/login/")
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert resp.data["detail"] == "Method not allowed."
        assert "POST" in resp.headers.get("Allow", "")

    def test_duplicate_email_lookup_returns_400(self, api_client, monkeypatch):
        """MultipleObjectsReturned during email lookup is treated as auth failure."""

        def raise_multiple(*args, **kwargs):
            raise User.MultipleObjectsReturned

        monkeypatch.setattr(User.objects, "get", raise_multiple)
        resp = api_client.post(
            "/api/auth/login/",
            {"email": "test@example.com", "password": "testpass123"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["detail"] == "Invalid credentials."

    def test_login_normalizes_email_before_lookup(self, api_client, user):
        """Login accepts equivalent emails with surrounding whitespace/case differences."""
        resp = api_client.post(
            "/api/auth/login/",
            {"email": "  TEST@EXAMPLE.COM  ", "password": "testpass123"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["username"] == "testuser"

    @override_settings(
        ACCOUNT_EMAIL_VERIFICATION="mandatory",
        FEATURE_EMAIL_VERIFICATION_ROLLOUT=True,
    )
    def test_unverified_login_returns_403_when_verification_is_mandatory(
        self, api_client, user
    ):
        """Unverified users are blocked when the rollout is active."""
        resp = api_client.post(
            "/api/auth/login/",
            {"email": "test@example.com", "password": "testpass123"},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.data["code"] == "email_not_verified"

    @override_settings(
        ACCOUNT_EMAIL_VERIFICATION="mandatory",
        FEATURE_EMAIL_VERIFICATION_ROLLOUT=False,
    )
    def test_unverified_login_allowed_when_rollout_is_disabled(self, api_client, user):
        """Existing users can still log in while rollout is disabled."""
        resp = api_client.post(
            "/api/auth/login/",
            {"email": "test@example.com", "password": "testpass123"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["username"] == "testuser"


@pytest.mark.django_db
class TestEmailVerificationFlow:
    """Tests for mandatory verification-specific auth behavior."""

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
    def test_registration_returns_verification_message_when_mandatory(self, api_client):
        """Mandatory verification registration should not return authenticated user data."""
        resp = api_client.post(
            "/api/auth/register/",
            {
                "email": "verify@example.com",
                "username": "verifyuser",
                "password": "newpass123",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert "detail" in resp.data
        assert "username" not in resp.data
        assert resp.data["code"] == "verification_pending"

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
    def test_resend_verification_anonymous_without_email_returns_200(self, api_client):
        """Anonymous resend without email returns 200 (no user enumeration)."""
        resp = api_client.post("/api/auth/resend-verification/")
        assert resp.status_code == status.HTTP_200_OK
        assert "verification email sent" in resp.data["detail"].lower()

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
    def test_resend_verification_anonymous_with_unknown_email_returns_200(
        self, api_client
    ):
        """Anonymous resend with unknown email returns 200 (no enumeration)."""
        resp = api_client.post(
            "/api/auth/resend-verification/",
            {"email": "nobody@example.com"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["detail"] == GENERIC_RESEND_DETAIL

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
    def test_resend_verification_anonymous_with_valid_email_returns_200(
        self, api_client, user
    ):
        """Anonymous resend with valid unverified email sends verification."""
        resp = api_client.post(
            "/api/auth/resend-verification/",
            {"email": user.email},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "verification email sent" in resp.data["detail"].lower()

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
    def test_resend_verification_anonymous_with_non_string_email_returns_200(
        self, api_client
    ):
        """Non-string email payloads do not hit ORM and still return uniform 200."""
        resp = api_client.post(
            "/api/auth/resend-verification/",
            {"email": [1]},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "verification email sent" in resp.data["detail"].lower()

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
    def test_resend_verification_returns_200_for_verified_user(self, auth_client, user):
        """Already-verified users get the same 200 response (no enumeration)."""
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=True,
            primary=True,
        )
        resp = auth_client.post("/api/auth/resend-verification/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["detail"] == GENERIC_RESEND_DETAIL

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
    def test_resend_verification_succeeds_for_unverified_user(self, auth_client):
        """Authenticated unverified users can request another verification email."""
        resp = auth_client.post("/api/auth/resend-verification/")
        assert resp.status_code == status.HTTP_200_OK

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
    def test_resend_verification_hides_smtp_failure_for_anonymous_known_email(
        self, api_client, user
    ):
        """SMTP failures still return 200 to avoid leaking valid unverified accounts."""
        with patch(
            "blog.api.write.router.send_verification_email_for_user",
            side_effect=smtplib.SMTPException("mail transport unavailable"),
        ):
            resp = api_client.post(
                "/api/auth/resend-verification/",
                {"email": user.email},
                format="json",
            )
        assert resp.status_code == status.HTTP_200_OK
        assert "verification email sent" in resp.data["detail"].lower()


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

    def test_unauthenticated_returns_403(self, api_client):
        """Unauthenticated requests are rejected; DRF SessionAuthentication returns 403."""
        resp = api_client.get("/api/auth/user/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


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

    def test_non_string_profile_fields_return_400(self, auth_client):
        """Non-string profile update fields return explicit validation errors."""
        resp = auth_client.patch(
            "/api/auth/profile/",
            {
                "username": {"$ne": ""},
                "current_password": {"$ne": ""},
                "new_password": ["bad"],
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["username"] == "Username must be a string."
        assert resp.data["new_password"] == "Password must be a string."


# ── Google OAuth ────────────────────────────────────────────────────────────────


def _make_social_request():
    """Build a minimal request with session for use with complete_social_login."""
    from importlib import import_module

    from django.contrib.auth.models import AnonymousUser
    from django.conf import settings
    from django.test import RequestFactory

    factory = RequestFactory()
    request = factory.get("/accounts/google/login/callback/")
    SessionStore = import_module(settings.SESSION_ENGINE).SessionStore
    request.session = SessionStore()
    request.session.save()
    request.user = AnonymousUser()
    return request


@pytest.mark.django_db
class TestGoogleOAuth:
    """Tests for Google OAuth login flow and social account integration."""

    # ── Redirect ────────────────────────────────────────────────────────────

    def test_google_login_endpoint_redirects(self, client):
        """POST /accounts/google/login/ triggers the OAuth redirect flow (302).
        SOCIALACCOUNT_LOGIN_ON_GET=False means GET returns a confirmation form (200);
        a POST is required to initiate the redirect.
        """
        resp = client.post("/accounts/google/login/")
        assert resp.status_code == status.HTTP_302_FOUND

    def test_google_login_redirect_targets_google(self, client):
        """The POST redirect URL points to accounts.google.com."""
        resp = client.post("/accounts/google/login/")
        location = resp.headers.get("Location", "")
        assert "accounts.google.com" in location

    # ── User & Profile creation ─────────────────────────────────────────────

    def test_social_user_gets_profile_via_signal(self, db):
        """A user created in any way (including via social login) auto-receives a Profile from signals."""
        from accounts.models import Profile

        # Simulate what allauth does after completing the OAuth flow: save the user.
        u = User.objects.create_user(username="g_newuser", email="g_new@example.com")
        assert Profile.objects.filter(user=u).exists()

    def test_social_account_is_linked_to_user(self, db):
        """A SocialAccount ties a Google uid to a specific User."""
        from allauth.socialaccount.models import SocialAccount

        u = User.objects.create_user(username="g_linked", email="g_linked@example.com")
        sa = SocialAccount.objects.create(
            user=u,
            provider="google",
            uid="google-uid-002",
            extra_data={"sub": "google-uid-002", "email": "g_linked@example.com"},
        )
        assert SocialAccount.objects.filter(
            user=u, provider="google", uid="google-uid-002"
        ).exists()
        assert sa.user == u

    def test_social_account_uid_is_unique_per_provider(self, db):
        """The same Google uid cannot be assigned to two different users."""
        from django.db import IntegrityError

        from allauth.socialaccount.models import SocialAccount

        u1 = User.objects.create_user(username="g_user1", email="g1@example.com")
        u2 = User.objects.create_user(username="g_user2", email="g2@example.com")
        SocialAccount.objects.create(
            user=u1, provider="google", uid="google-uid-003", extra_data={}
        )
        with pytest.raises(IntegrityError):
            SocialAccount.objects.create(
                user=u2, provider="google", uid="google-uid-003", extra_data={}
            )

    # ── API access for social users ─────────────────────────────────────────

    def test_social_user_can_access_current_user_endpoint(self, db):
        """A user created via social login can access /api/auth/user/ when authenticated."""
        from accounts.models import Profile

        social_user = User.objects.create_user(
            username="g_apiuser",
            email="g_api@example.com",
            password=None,
        )
        Profile.objects.get_or_create(user=social_user)

        client = APIClient()
        client.force_authenticate(user=social_user)
        resp = client.get("/api/auth/user/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["email"] == "g_api@example.com"

    def test_social_user_without_auth_cannot_access_user_endpoint(self, db):
        """An unauthenticated request is still rejected even for OAuth-created accounts."""
        client = APIClient()
        resp = client.get("/api/auth/user/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    # ── ensure_sites_migrations command ────────────────────────────────────

    @pytest.mark.skipif(
        connection.vendor != "postgresql",
        reason="ensure_sites_migrations uses PostgreSQL information_schema",
    )
    def test_ensure_sites_migrations_is_idempotent(self, db):
        """Running ensure_sites_migrations on a healthy PostgreSQL DB produces no error."""
        from django.core.management import call_command

        call_command("ensure_sites_migrations", stdout=io.StringIO())
