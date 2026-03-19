import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from organizations.models import Organization, OrganizationMember
from organizations.services import delete_organization
from projects.models import Project

UserProfile = get_user_model()


class DeleteOrganizationTests(TestCase):
    def setUp(self):
        self.admin = UserProfile.objects.create_user(
            username="orgadmin", email="admin@example.com", password="pass123"
        )
        self.member = UserProfile.objects.create_user(
            username="orgmember", email="member@example.com", password="pass123"
        )
        self.org = Organization.objects.create(
            name="Test Org", email="org@example.com", stripe_customer_id=""
        )
        OrganizationMember.objects.create(
            user=self.admin, organization=self.org, role="admin"
        )
        OrganizationMember.objects.create(
            user=self.member, organization=self.org, role="member"
        )

    def test_non_admin_cannot_delete(self):
        resp = delete_organization(self.member, self.org.id)
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Organization.objects.filter(id=self.org.id).exists())

    def test_blocks_deletion_with_active_projects(self):
        Project.objects.create(name="Project 1", organization=self.org)
        resp = delete_organization(self.admin, self.org.id)
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content)
        self.assertIn("active projects", data["error"])
        self.assertEqual(data["project_count"], 1)
        self.assertTrue(Organization.objects.filter(id=self.org.id).exists())

    def test_blocks_deletion_with_multiple_projects(self):
        Project.objects.create(name="Project 1", organization=self.org)
        Project.objects.create(name="Project 2", organization=self.org)
        resp = delete_organization(self.admin, self.org.id)
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content)
        self.assertEqual(data["project_count"], 2)
        self.assertTrue(Organization.objects.filter(id=self.org.id).exists())

    def test_allows_deletion_with_no_projects(self):
        resp = delete_organization(self.admin, self.org.id)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Organization.objects.filter(id=self.org.id).exists())

    def test_nonexistent_org_raises_404(self):
        from django.http import Http404
        with self.assertRaises(Http404):
            delete_organization(self.admin, "nonexistent_id_here")
