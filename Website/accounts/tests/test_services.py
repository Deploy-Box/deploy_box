from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.services import (
    get_profile,
    update_profile,
    delete_account,
    signup_regular,
    signup_with_invite,
    get_or_create_workos_user,
    extract_workos_session_id,
    get_workos_logout_url,
    ServiceError,
    ValidationError,
)
from organizations.models import Organization, OrganizationMember, PendingInvites

UserProfile = get_user_model()


class GetProfileTest(TestCase):
    def test_returns_profile_dict(self):
        user = UserProfile.objects.create_user(
            username="alice", email="alice@example.com", password="pw",
            first_name="Alice", last_name="Smith",
        )
        result = get_profile(user)
        self.assertEqual(result["username"], "alice")
        self.assertEqual(result["email"], "alice@example.com")
        self.assertEqual(result["first_name"], "Alice")
        self.assertEqual(result["last_name"], "Smith")


class UpdateProfileTest(TestCase):
    def setUp(self):
        self.user = UserProfile.objects.create_user(
            username="alice", email="alice@example.com", password="pw",
        )

    def test_update_username(self):
        result = update_profile(self.user, {"username": "alice_new"})
        self.assertIn("Profile updated", result["message"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "alice_new")

    def test_update_email(self):
        result = update_profile(self.user, {"email": "new@example.com"})
        self.assertIn("Profile updated", result["message"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.com")

    def test_duplicate_username_raises(self):
        UserProfile.objects.create_user(username="bob", password="pw")
        with self.assertRaises(ValidationError) as ctx:
            update_profile(self.user, {"username": "bob"})
        self.assertIn("already taken", str(ctx.exception))

    def test_duplicate_email_raises(self):
        UserProfile.objects.create_user(
            username="bob", email="bob@example.com", password="pw",
        )
        with self.assertRaises(ValidationError) as ctx:
            update_profile(self.user, {"email": "bob@example.com"})
        self.assertIn("already taken", str(ctx.exception))

    def test_same_username_no_error(self):
        result = update_profile(self.user, {"username": "alice"})
        self.assertIn("Profile updated", result["message"])

    def test_empty_data_is_noop(self):
        result = update_profile(self.user, {})
        self.assertIn("Profile updated", result["message"])


class DeleteAccountTest(TestCase):
    def test_deletes_user_and_flushes_session(self):
        user = UserProfile.objects.create_user(username="alice", password="pw")
        user_id = user.id
        mock_session = MagicMock()
        result = delete_account(user, mock_session)
        self.assertEqual(result["message"], "Account deleted successfully")
        mock_session.flush.assert_called_once()
        self.assertFalse(UserProfile.objects.filter(id=user_id).exists())


class SignupRegularTest(TestCase):
    def test_creates_user(self):
        user = UserProfile.objects.create_user(
            username="newuser", email="new@example.com", password="pw",
        )
        save_fn = MagicMock(return_value=user)
        result = signup_regular({"email": "new@example.com"}, save_fn)
        save_fn.assert_called_once()
        self.assertEqual(result["user_id"], str(user.id))
        self.assertIn("created successfully", result["message"])

    def test_auto_joins_pending_invite(self):
        org = Organization.objects.create(
            name="Org", email="org@test.com", stripe_customer_id="cus_fake"
        )
        PendingInvites.objects.create(organization=org, email="invited@test.com")

        user = UserProfile.objects.create_user(
            username="invited", email="invited@test.com", password="pw",
        )
        save_fn = MagicMock(return_value=user)
        result = signup_regular({"email": "invited@test.com"}, save_fn)

        self.assertIn("organization_id", result)
        self.assertTrue(
            OrganizationMember.objects.filter(user=user, organization=org).exists()
        )
        self.assertFalse(
            PendingInvites.objects.filter(email="invited@test.com").exists()
        )


class SignupWithInviteTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Org", email="org@test.com", stripe_customer_id="cus_fake"
        )
        self.invite = PendingInvites.objects.create(
            organization=self.org, email="invited@test.com"
        )

    def test_valid_invite_joins_org(self):
        user = UserProfile.objects.create_user(
            username="invited", email="invited@test.com", password="pw",
        )
        save_fn = MagicMock(return_value=user)
        result = signup_with_invite(
            {"email": "invited@test.com"}, save_fn, str(self.invite.id)
        )
        self.assertIn("organization_id", result)
        self.assertTrue(
            OrganizationMember.objects.filter(user=user, organization=self.org).exists()
        )
        self.assertFalse(PendingInvites.objects.filter(id=self.invite.id).exists())

    def test_invalid_invite_raises(self):
        user = UserProfile.objects.create_user(
            username="someone", email="someone@test.com", password="pw",
        )
        save_fn = MagicMock(return_value=user)
        with self.assertRaises(ValidationError) as ctx:
            signup_with_invite({"email": "someone@test.com"}, save_fn, "bad_invite_id")
        self.assertIn("Invalid or expired", str(ctx.exception))

    def test_email_mismatch_raises(self):
        user = UserProfile.objects.create_user(
            username="wrong", email="wrong@test.com", password="pw",
        )
        save_fn = MagicMock(return_value=user)
        with self.assertRaises(ValidationError) as ctx:
            signup_with_invite(
                {"email": "wrong@test.com"}, save_fn, str(self.invite.id)
            )
        self.assertIn("Email must match", str(ctx.exception))


class GetOrCreateWorkOSUserTest(TestCase):
    def test_creates_new_user(self):
        data = {
            "workos_user_id": "wos_abc",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
        }
        user = get_or_create_workos_user(data)
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(user.workos_user_id, "wos_abc")
        self.assertEqual(user.auth_provider, "workos")
        self.assertFalse(user.has_usable_password())

    def test_finds_by_workos_user_id(self):
        existing = UserProfile.objects.create_user(
            username="existing", email="e@example.com", password="pw",
            workos_user_id="wos_existing",
        )
        data = {
            "workos_user_id": "wos_existing",
            "email": "e@example.com",
            "first_name": "E",
            "last_name": "User",
        }
        user = get_or_create_workos_user(data)
        self.assertEqual(user.pk, existing.pk)

    def test_links_existing_user_by_email(self):
        existing = UserProfile.objects.create_user(
            username="local", email="local@example.com", password="pw",
        )
        data = {
            "workos_user_id": "wos_link",
            "email": "local@example.com",
            "first_name": "L",
            "last_name": "User",
        }
        user = get_or_create_workos_user(data)
        self.assertEqual(user.pk, existing.pk)
        user.refresh_from_db()
        self.assertEqual(user.workos_user_id, "wos_link")
        self.assertEqual(user.auth_provider, "workos")

    def test_handles_duplicate_username(self):
        UserProfile.objects.create_user(
            username="alice", email="alice@existing.com", password="pw",
        )
        data = {
            "workos_user_id": "wos_dup",
            "email": "alice@new.com",
            "first_name": "Alice",
            "last_name": "New",
        }
        user = get_or_create_workos_user(data)
        # Username should be alice1 since alice is taken
        self.assertEqual(user.username, "alice1")


class ExtractWorkOSSessionIdTest(TestCase):
    def test_extracts_sid_from_jwt(self):
        import jwt as pyjwt
        token = pyjwt.encode({"sid": "sess_123"}, "fake-secret", algorithm="HS256")
        result = extract_workos_session_id(token)
        self.assertEqual(result, "sess_123")

    def test_returns_none_on_invalid_token(self):
        result = extract_workos_session_id("not.a.jwt")
        self.assertIsNone(result)


class GetWorkOSLogoutUrlTest(TestCase):
    def test_returns_none_when_no_session_id(self):
        self.assertIsNone(get_workos_logout_url(None))

    @patch("accounts.services.settings")
    def test_returns_none_in_dev_mode(self, mock_settings):
        """In dev, WorkOS credentials are None so the client raises and we get None."""
        mock_settings.ENV = "DEV"
        mock_settings.WORKOS = {"API_KEY": None, "CLIENT_ID": None}
        mock_settings.HOST = "http://localhost:8000"
        self.assertIsNone(get_workos_logout_url("sess_123"))
