from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import TestCase

from organizations.models import Organization, OrganizationMember
from projects.models import Project, ProjectMember
from projects.services import (
    create_project,
    get_projects,
    update_project,
    delete_project,
    ForbiddenError,
    NotFoundError,
)

UserProfile = get_user_model()


class _ProjectTestMixin:
    """Shared setup for project service tests."""

    def _make_org_with_admin(self, user, tier="consumption"):
        org = Organization.objects.create(
            name="Test Org", email="org@test.com",
            stripe_customer_id="cus_fake", tier=tier,
        )
        OrganizationMember.objects.create(user=user, organization=org, role="admin")
        return org


class CreateProjectTest(_ProjectTestMixin, TestCase):
    def setUp(self):
        self.user = UserProfile.objects.create_user(username="alice", password="pw")
        self.org = self._make_org_with_admin(self.user)

    def test_creates_project(self):
        result = create_project(
            user=self.user, name="My Project",
            description="desc", organization_id=self.org.id,
        )
        self.assertEqual(result["name"], "My Project")
        self.assertTrue(Project.objects.filter(id=result["id"]).exists())

    def test_creates_admin_membership(self):
        result = create_project(
            user=self.user, name="P1", organization_id=self.org.id,
        )
        member = ProjectMember.objects.get(project_id=result["id"], user=self.user)
        self.assertEqual(member.role, "admin")

    def test_non_member_cannot_create(self):
        outsider = UserProfile.objects.create_user(username="bob", password="pw")
        with self.assertRaises(ForbiddenError):
            create_project(
                user=outsider, name="Forbidden",
                organization_id=self.org.id,
            )

    def test_nonexistent_org_raises_404(self):
        with self.assertRaises(Http404):
            create_project(
                user=self.user, name="Ghost",
                organization_id="nonexistent_id_xx",
            )

    def test_free_tier_project_limit(self):
        free_org = self._make_org_with_admin(self.user, tier="free")
        create_project(
            user=self.user, name="First",
            organization_id=free_org.id,
        )
        with self.assertRaises(ForbiddenError) as ctx:
            create_project(
                user=self.user, name="Second",
                organization_id=free_org.id,
            )
        self.assertIn("limited to 1 project", str(ctx.exception))


class GetProjectsTest(_ProjectTestMixin, TestCase):
    def setUp(self):
        self.user = UserProfile.objects.create_user(username="alice", password="pw")
        self.org = self._make_org_with_admin(self.user)

    def test_returns_projects_for_user(self):
        p = Project.objects.create(name="P1", organization=self.org)
        ProjectMember.objects.create(user=self.user, project=p, role="admin")
        result = get_projects(self.user)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "P1")

    def test_returns_empty_when_no_membership(self):
        outsider = UserProfile.objects.create_user(username="bob", password="pw")
        result = get_projects(outsider)
        self.assertEqual(result, [])


class UpdateProjectTest(_ProjectTestMixin, TestCase):
    def setUp(self):
        self.user = UserProfile.objects.create_user(username="alice", password="pw")
        self.org = self._make_org_with_admin(self.user)
        self.project = Project.objects.create(
            name="Original", description="old", organization=self.org,
        )
        ProjectMember.objects.create(
            user=self.user, project=self.project, role="admin",
        )

    def test_updates_name_and_description(self):
        result = update_project(self.project.id, "New Name", "new desc", self.user)
        self.assertEqual(result["name"], "New Name")
        self.assertEqual(result["description"], "new desc")

    def test_nonexistent_project_raises(self):
        with self.assertRaises(NotFoundError):
            update_project("nonexistent_id_xx", "x", "x", self.user)

    def test_non_member_cannot_update(self):
        outsider = UserProfile.objects.create_user(username="bob", password="pw")
        with self.assertRaises(ForbiddenError):
            update_project(self.project.id, "Hack", "hacked", outsider)


class DeleteProjectTest(_ProjectTestMixin, TestCase):
    def setUp(self):
        self.user = UserProfile.objects.create_user(username="alice", password="pw")
        self.org = self._make_org_with_admin(self.user)
        self.project = Project.objects.create(
            name="ToDelete", organization=self.org,
        )
        ProjectMember.objects.create(
            user=self.user, project=self.project, role="admin",
        )

    def test_deletes_project(self):
        pid = self.project.id
        result = delete_project(pid, self.user)
        self.assertIn("deleted", result["message"])
        self.assertFalse(Project.objects.filter(id=pid).exists())

    def test_nonexistent_raises(self):
        with self.assertRaises(NotFoundError):
            delete_project("nonexistent_id_xx", self.user)

    def test_non_member_cannot_delete(self):
        outsider = UserProfile.objects.create_user(username="bob", password="pw")
        with self.assertRaises(ForbiddenError):
            delete_project(self.project.id, outsider)