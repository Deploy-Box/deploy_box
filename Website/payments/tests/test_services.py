from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone

from organizations.models import Organization
from payments.models import Invoice, InvoiceLineItem, RateCard
from payments.services import generate_monthly_invoices, ensure_stripe_customer, create_stripe_customer
from payments.tests.test_models import _PaymentsTestMixin
from stacks.metrics.models import MetricDefinition, MetricUsageRecord
from stacks.models import PurchasableStack, Stack
from projects.models import Project


class EnsureStripeCustomerTestCase(TestCase):
    @patch('payments.services.stripe')
    def test_creates_customer_when_missing(self, mock_stripe):
        org = Organization.objects.create(name="Org", email="o@t.com", stripe_customer_id="")
        mock_customer = MagicMock()
        mock_customer.id = 'cus_new'
        mock_stripe.Customer.create.return_value = mock_customer

        result = ensure_stripe_customer(org)

        self.assertEqual(result, 'cus_new')
        org.refresh_from_db()
        self.assertEqual(org.stripe_customer_id, 'cus_new')
        _, kwargs = mock_stripe.Customer.create.call_args
        self.assertIn('idempotency_key', kwargs)

    @patch('payments.services.stripe')
    def test_skips_if_already_exists(self, mock_stripe):
        org = Organization.objects.create(name="Org", email="o@t.com", stripe_customer_id="cus_existing")
        result = ensure_stripe_customer(org)
        self.assertEqual(result, 'cus_existing')
        mock_stripe.Customer.create.assert_not_called()


class GenerateMonthlyInvoicesTestCase(_PaymentsTestMixin, TestCase):
    def setUp(self):
        self.org, self.proj, self.stack = self._make_org_project_stack()
        self.metric = self._make_metric("cpu_hours")
        self.rate_card = RateCard.objects.create(
            metric_definition=self.metric,
            pricing_model="per_unit",
            price_per_unit=Decimal("0.50"),
        )
        for day in [5, 10, 15, 20]:
            MetricUsageRecord.objects.create(
                metric_definition=self.metric,
                stack=self.stack,
                resource="test_resource",
                amount_used=Decimal("10.000000"),
                usage_datetime=timezone.make_aware(
                    timezone.datetime(2025, 3, day, 12, 0)
                ),
            )

    @patch('payments.services.create_invoice')
    def test_generates_invoice_with_correct_totals(self, mock_create_invoice):
        """Should create an invoice with correct line items and totals."""
        mock_create_invoice.return_value = ("in_test", "https://stripe.com/inv")

        results = generate_monthly_invoices(billing_month=date(2025, 3, 1))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "success")

        invoice = Invoice.objects.get(organization=self.org, invoice_month=date(2025, 3, 1))
        self.assertEqual(invoice.status, "draft")
        # 4 records × 10 units = 40 units × $0.50 = $20.00
        self.assertEqual(invoice.total_amount, Decimal("20.00"))

        line_items = invoice.line_items.all()
        self.assertEqual(line_items.count(), 1)
        self.assertEqual(line_items.first().units_used, Decimal("40.000000"))
        self.assertEqual(line_items.first().line_amount, Decimal("20.00"))

    @patch('payments.services.create_invoice')
    def test_idempotent_rerun(self, mock_create_invoice):
        """Running twice for the same month should not duplicate line items."""
        mock_create_invoice.return_value = ("in_test", "https://stripe.com/inv")

        generate_monthly_invoices(billing_month=date(2025, 3, 1))
        generate_monthly_invoices(billing_month=date(2025, 3, 1))

        invoices = Invoice.objects.filter(organization=self.org, invoice_month=date(2025, 3, 1))
        self.assertEqual(invoices.count(), 1)
        self.assertEqual(invoices.first().line_items.count(), 1)

    @patch('payments.services.create_invoice')
    def test_no_usage_no_invoice(self, mock_create_invoice):
        """No usage records means no invoices generated."""
        results = generate_monthly_invoices(billing_month=date(2024, 1, 1))
        self.assertEqual(len(results), 0)

    @patch('payments.services.create_invoice')
    def test_missing_rate_card_skips_line_item(self, mock_create_invoice):
        """If no RateCard exists for a metric, skip the line item."""
        mock_create_invoice.return_value = None
        self.rate_card.delete()

        results = generate_monthly_invoices(billing_month=date(2025, 3, 1))

        invoice = Invoice.objects.get(organization=self.org, invoice_month=date(2025, 3, 1))
        self.assertEqual(invoice.line_items.count(), 0)
        self.assertEqual(invoice.total_amount, Decimal("0.00"))

    @patch('payments.services.create_invoice')
    def test_syncs_to_stripe_when_customer_exists(self, mock_create_invoice):
        """Should sync to Stripe if org has stripe_customer_id and total > 0."""
        mock_create_invoice.return_value = ("in_stripe_123", "https://stripe.com/inv")

        results = generate_monthly_invoices(billing_month=date(2025, 3, 1))

        mock_create_invoice.assert_called_once()
        invoice = Invoice.objects.get(organization=self.org, invoice_month=date(2025, 3, 1))
        self.assertEqual(invoice.stripe_invoice_id, "in_stripe_123")

    @patch('payments.services.create_invoice')
    def test_no_stripe_sync_without_customer_id(self, mock_create_invoice):
        """Should NOT sync to Stripe if org has no stripe_customer_id."""
        self.org.stripe_customer_id = ""
        self.org.save()

        results = generate_monthly_invoices(billing_month=date(2025, 3, 1))

        mock_create_invoice.assert_not_called()
