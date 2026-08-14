from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from organizations.models import Organization, OrganizationMember, PendingInvites
from organizations.services import (
    get_organizations,
    get_organization,
    create_organization,
    update_organization,
    add_org_member,
    remove_org_member,
    leave_organization,
    invite_new_user_to_org,
    remove_pending_invite,
    ForbiddenError,
    NotFoundError,
    ServiceError,
)
from projects.models import Project

UserProfile = get_user_model()


class _OrgTestMixin:
    def _make_user(self, username, email=None):
        email = email or f"{username}@test.com"
        return UserProfile.objects.create_user(
            username=username, email=email, password="pw",
        )

    def _make_org(self, name="Org", admin=None, tier="consumption"):
        org = Organization.objects.create(
            name=name, email=f"{name.lower()}@t.com",
            stripe_customer_id="cus_fake", tier=tier,
        )
        if admin:
            OrganizationMember.objects.create(
                user=admin, organization=org, role="admin",
            )
        return org


class GetOrganizationsTest(_OrgTestMixin, TestCase):
    def test_returns_user_orgs(self):
        user = self._make_user("alice")
        org = self._make_org("Alice Org", admin=user)
        result = get_organizations(user)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, org.id)

    def test_returns_empty_for_no_membership(self):
        user = self._make_user("bob")
        result = get_organizations(user)
        self.assertEqual(result, [])


class GetOrganizationTest(_OrgTestMixin, TestCase):
    def test_returns_org_for_member(self):
        user = self._make_user("alice")
        org = self._make_org("Org", admin=user)
        result = get_organization(user, org.id)
        self.assertEqual(result.id, org.id)

    def test_returns_none_for_non_member(self):
        user = self._make_user("alice")
        org = self._make_org("Org")
        result = get_organization(user, org.id)
        self.assertIsNone(result)

    def test_returns_none_for_nonexistent_org(self):
        user = self._make_user("alice")
        result = get_organization(user, "nonexistent_xxx")
        self.assertIsNone(result)


class CreateOrganizationTest(_OrgTestMixin, TestCase):
    @patch("organizations.services.create_stripe_customer", return_value="cus_new")
    def test_creates_org_and_welcome_project(self, _mock_stripe):
        user = self._make_user("alice")
        result = create_organization(user, "New Org", "new@test.com")
        self.assertIn("id", result)
        self.assertEqual(result["name"], "New Org")
        org = Organization.objects.get(id=result["id"])
        self.assertTrue(
            OrganizationMember.objects.filter(
                user=user, organization=org, role="admin"
            ).exists()
        )
        self.assertTrue(
            Project.objects.filter(
                organization=org, name="Welcome Project"
            ).exists()
        )

    @patch("organizations.services.create_stripe_customer", return_value="cus_new")
    def test_free_tier_limit_blocks_second_org(self, _mock_stripe):
        user = self._make_user("alice")
        self._make_org("Existing Free", admin=user, tier="free")
        result = create_organization(user, "Second Org", "two@test.com")
        self.assertIn("error", result)
        self.assertIn("Free plan", result["error"])


class UpdateOrganizationTest(_OrgTestMixin, TestCase):
    def test_admin_can_update(self):
        user = self._make_user("alice")
        org = self._make_org("Org", admin=user)
        result = update_organization(user, org.id, {"name": "Renamed"})
        self.assertIn("updated", result["message"])
        org.refresh_from_db()
        self.assertEqual(org.name, "Renamed")

    def test_non_admin_cannot_update(self):
        admin = self._make_user("admin")
        member = self._make_user("member")
        org = self._make_org("Org", admin=admin)
        OrganizationMember.objects.create(user=member, organization=org, role="member")
        # check_permisssion uses get_object_or_404 for admin role → raises Http404
        from django.http import Http404
        with self.assertRaises(Http404):
            update_organization(member, org.id, {"name": "Hacked"})


class AddOrgMemberTest(_OrgTestMixin, TestCase):
    def test_admin_can_add_member(self):
        admin = self._make_user("admin")
        new_user = self._make_user("newguy")
        org = self._make_org("Org", admin=admin)
        result = add_org_member(admin, org.id, "newguy", "member")
        self.assertIn("added", result["message"])
        self.assertTrue(
            OrganizationMember.objects.filter(
                user=new_user, organization=org
            ).exists()
        )

    def test_duplicate_member_raises(self):
        admin = self._make_user("admin")
        member = self._make_user("member")
        org = self._make_org("Org", admin=admin)
        OrganizationMember.objects.create(user=member, organization=org, role="member")
        with self.assertRaises(ServiceError) as ctx:
            add_org_member(admin, org.id, "member", "member")
        self.assertIn("already a member", str(ctx.exception))

    def test_nonexistent_user_raises(self):
        admin = self._make_user("admin")
        org = self._make_org("Org", admin=admin)
        with self.assertRaises(NotFoundError):
            add_org_member(admin, org.id, "ghost_user", "member")


class RemoveOrgMemberTest(_OrgTestMixin, TestCase):
    def test_admin_can_remove_member(self):
        admin = self._make_user("admin")
        member = self._make_user("member")
        org = self._make_org("Org", admin=admin)
        OrganizationMember.objects.create(user=member, organization=org, role="member")
        result = remove_org_member(admin, org.id, member.id)
        self.assertIn("removed", result["message"])
        self.assertFalse(
            OrganizationMember.objects.filter(user=member, organization=org).exists()
        )

    def test_cannot_remove_self(self):
        admin = self._make_user("admin")
        org = self._make_org("Org", admin=admin)
        with self.assertRaises(ServiceError) as ctx:
            remove_org_member(admin, org.id, admin.id)
        self.assertIn("cannot remove yourself", str(ctx.exception))


class LeaveOrganizationTest(_OrgTestMixin, TestCase):
    def test_member_leave_blocked_by_permission_check(self):
        # BUG: check_permisssion only handles requeired_role=None and "admin",
        # so leave_organization (which passes "member") always raises ForbiddenError.
        admin = self._make_user("admin")
        member = self._make_user("member")
        org = self._make_org("Org", admin=admin)
        OrganizationMember.objects.create(user=member, organization=org, role="member")
        with self.assertRaises(ForbiddenError):
            leave_organization(member, org.id)


class InviteNewUserTest(_OrgTestMixin, TestCase):
    @patch("organizations.services.invite_org_member")
    def test_creates_pending_invite(self, _mock_email):
        admin = self._make_user("admin")
        org = self._make_org("Org", admin=admin)
        result = invite_new_user_to_org(admin, org, "new@test.com")
        self.assertIn("invite", result["message"])
        self.assertTrue(
            PendingInvites.objects.filter(
                organization=org, email="new@test.com"
            ).exists()
        )


class RemovePendingInviteTest(_OrgTestMixin, TestCase):
    def test_admin_removes_invite(self):
        admin = self._make_user("admin")
        org = self._make_org("Org", admin=admin)
        invite = PendingInvites.objects.create(organization=org, email="x@test.com")
        result = remove_pending_invite(admin, org.id, invite.id)
        self.assertTrue(result["success"])
        self.assertFalse(PendingInvites.objects.filter(id=invite.id).exists())

    def test_nonexistent_invite_raises(self):
        admin = self._make_user("admin")
        org = self._make_org("Org", admin=admin)
        with self.assertRaises(NotFoundError):
            remove_pending_invite(admin, org.id, "bad_invite_id")


class FreeTierLimitsTest(_OrgTestMixin, TestCase):
    def test_has_reached_free_org_limit(self):
        user = self._make_user("alice")
        self._make_org("Free Org", admin=user, tier="free")
        self.assertTrue(Organization.has_reached_free_org_limit(user))

    def test_consumption_org_does_not_count(self):
        user = self._make_user("alice")
        self._make_org("Paid Org", admin=user, tier="consumption")
        self.assertFalse(Organization.has_reached_free_org_limit(user))

    def test_has_reached_free_project_limit(self):
        user = self._make_user("alice")
        org = self._make_org("Org", admin=user, tier="free")
        Project.objects.create(name="P1", organization=org)
        self.assertTrue(org.has_reached_free_project_limit())

    def test_consumption_org_no_project_limit(self):
        user = self._make_user("alice")
        org = self._make_org("Org", admin=user, tier="consumption")
        Project.objects.create(name="P1", organization=org)
        self.assertFalse(org.has_reached_free_project_limit())
