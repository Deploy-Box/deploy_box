from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import TestCase

from organizations.models import Organization, OrganizationMember
from organizations.services import (
    delete_organization,
    ForbiddenError,
    ServiceError,
)
from payments.models import Invoice
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
        with self.assertRaises(ForbiddenError) as ctx:
            delete_organization(self.member, self.org.id)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertTrue(Organization.objects.filter(id=self.org.id).exists())

    def test_blocks_deletion_with_active_projects(self):
        Project.objects.create(name="Project 1", organization=self.org)
        with self.assertRaises(ServiceError) as ctx:
            delete_organization(self.admin, self.org.id)
        self.assertIn("active projects", str(ctx.exception))
        self.assertTrue(Organization.objects.filter(id=self.org.id).exists())

    def test_blocks_deletion_with_multiple_projects(self):
        Project.objects.create(name="Project 1", organization=self.org)
        Project.objects.create(name="Project 2", organization=self.org)
        with self.assertRaises(ServiceError) as ctx:
            delete_organization(self.admin, self.org.id)
        self.assertIn("active projects", str(ctx.exception))
        self.assertTrue(Organization.objects.filter(id=self.org.id).exists())

    def test_allows_deletion_with_no_projects(self):
        result = delete_organization(self.admin, self.org.id)
        self.assertEqual(result["message"], "organization deleted")
        self.assertFalse(Organization.objects.filter(id=self.org.id).exists())

    def test_blocks_deletion_with_pending_draft_invoice(self):
        Invoice.objects.create(
            organization=self.org, invoice_month="2026-03-01", status="draft",
            subtotal_amount=100, tax_amount=10, total_amount=110,
        )
        with self.assertRaises(ServiceError) as ctx:
            delete_organization(self.admin, self.org.id)
        self.assertIn("pending invoices", str(ctx.exception))
        self.assertTrue(Organization.objects.filter(id=self.org.id).exists())

    def test_blocks_deletion_with_open_invoice(self):
        Invoice.objects.create(
            organization=self.org, invoice_month="2026-03-01", status="open",
            subtotal_amount=50, tax_amount=5, total_amount=55,
        )
        with self.assertRaises(ServiceError) as ctx:
            delete_organization(self.admin, self.org.id)
        self.assertIn("pending invoices", str(ctx.exception))
        self.assertTrue(Organization.objects.filter(id=self.org.id).exists())

    def test_allows_deletion_with_paid_invoices_only(self):
        Invoice.objects.create(
            organization=self.org, invoice_month="2026-03-01", status="paid",
            subtotal_amount=100, tax_amount=10, total_amount=110,
        )
        result = delete_organization(self.admin, self.org.id)
        self.assertEqual(result["message"], "organization deleted")
        self.assertFalse(Organization.objects.filter(id=self.org.id).exists())

    def test_nonexistent_org_raises_404(self):
        with self.assertRaises(Http404):
            delete_organization(self.admin, "nonexistent_id_here")
