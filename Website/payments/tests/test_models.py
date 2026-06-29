from decimal import Decimal

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase

from organizations.models import Organization
from payments.models import RateCard, Invoice, InvoiceLineItem
from projects.models import Project
from stacks.models import PurchasableStack, Stack
from stacks.metrics.models import MetricDefinition

UserProfile = get_user_model()


class _PaymentsTestMixin:
    """Shared helpers for payments tests."""

    def _make_metric(self, name="cpu_hours"):
        return MetricDefinition.objects.create(
            name=name,
            applicable_resources=["stacks_azurermcontainerapp"],
            unit_name="Hours",
            record_frequency_cron="0 * * * *",
        )

    def _make_org_project_stack(self):
        org = Organization.objects.create(
            name="Org", email="o@t.com", stripe_customer_id="cus_f",
        )
        proj = Project.objects.create(name="Proj", organization=org)
        purchasable = PurchasableStack.objects.create(
            name="Basic", description="d", price_id="pi", variant="v",
        )
        stack = Stack.objects.create(
            name="S1", project=proj, purchased_stack=purchasable,
        )
        return org, proj, stack


# ── RateCard validation ─────────────────────────────────────────────────────

class RateCardFlatRateTest(_PaymentsTestMixin, TestCase):
    def test_flat_rate_saves_with_price(self):
        m = self._make_metric()
        rc = RateCard(metric_definition=m, pricing_model="flat_rate", flat_rate_price=Decimal("9.99"))
        rc.save()
        self.assertEqual(rc.flat_rate_price, Decimal("9.99"))
        self.assertIsNone(rc.price_per_unit)
        self.assertIsNone(rc.tiered_pricing_json)

    def test_flat_rate_missing_price_raises(self):
        m = self._make_metric()
        rc = RateCard(metric_definition=m, pricing_model="flat_rate", flat_rate_price=None)
        with self.assertRaises(ValidationError):
            rc.save()


class RateCardPerUnitTest(_PaymentsTestMixin, TestCase):
    def test_per_unit_saves_with_price(self):
        m = self._make_metric()
        rc = RateCard(metric_definition=m, pricing_model="per_unit", price_per_unit=Decimal("0.05"))
        rc.save()
        self.assertEqual(rc.price_per_unit, Decimal("0.05"))
        self.assertIsNone(rc.flat_rate_price)

    def test_per_unit_missing_price_raises(self):
        m = self._make_metric()
        rc = RateCard(metric_definition=m, pricing_model="per_unit", price_per_unit=None)
        with self.assertRaises(ValidationError):
            rc.save()


class RateCardTieredTest(_PaymentsTestMixin, TestCase):
    def test_tiered_saves_with_valid_json(self):
        m = self._make_metric()
        tiers = [
            {"up_to": 100, "price_per_unit": 0.10},
            {"up_to": None, "price_per_unit": 0.05},
        ]
        rc = RateCard(metric_definition=m, pricing_model="tiered", tiered_pricing_json=tiers)
        rc.save()
        self.assertIsNone(rc.flat_rate_price)
        self.assertIsNone(rc.price_per_unit)

    def test_tiered_missing_json_raises(self):
        m = self._make_metric()
        rc = RateCard(metric_definition=m, pricing_model="tiered", tiered_pricing_json=None)
        with self.assertRaises(ValidationError):
            rc.save()

    def test_tiered_invalid_tier_structure_raises(self):
        m = self._make_metric()
        tiers = [{"bad_key": 100}]
        rc = RateCard(metric_definition=m, pricing_model="tiered", tiered_pricing_json=tiers)
        with self.assertRaises(ValidationError):
            rc.save()


# ── InvoiceLineItem pricing calculation ─────────────────────────────────────

class InvoiceLineItemFlatRateTest(_PaymentsTestMixin, TestCase):
    def test_flat_rate_sets_line_amount_to_flat_price(self):
        org, proj, stack = self._make_org_project_stack()
        m = self._make_metric()
        rc = RateCard.objects.create(
            metric_definition=m, pricing_model="flat_rate",
            flat_rate_price=Decimal("25.00"),
        )
        inv = Invoice.objects.create(
            organization=org, invoice_month="2026-03-01",
            subtotal_amount=0, tax_amount=0, total_amount=0,
        )
        item = InvoiceLineItem(
            invoice=inv, stack=stack, description="CPU",
            rate_card=rc, units_used=Decimal("999"), line_amount=Decimal("0"),
        )
        item.save()
        self.assertEqual(item.line_amount, Decimal("25.00"))


class InvoiceLineItemPerUnitTest(_PaymentsTestMixin, TestCase):
    def test_per_unit_calculates_units_times_price(self):
        org, proj, stack = self._make_org_project_stack()
        m = self._make_metric()
        rc = RateCard.objects.create(
            metric_definition=m, pricing_model="per_unit",
            price_per_unit=Decimal("0.10"),
        )
        inv = Invoice.objects.create(
            organization=org, invoice_month="2026-03-01",
            subtotal_amount=0, tax_amount=0, total_amount=0,
        )
        item = InvoiceLineItem(
            invoice=inv, stack=stack, description="CPU",
            rate_card=rc, units_used=Decimal("150"), line_amount=Decimal("0"),
        )
        item.save()
        self.assertEqual(item.line_amount, Decimal("15.000000"))


class InvoiceLineItemTieredPricingTest(_PaymentsTestMixin, TestCase):
    def _create_tiered_rate_card(self):
        m = self._make_metric()
        tiers = [
            {"up_to": 100, "price_per_unit": 0.10},
            {"up_to": 500, "price_per_unit": 0.08},
            {"up_to": None, "price_per_unit": 0.05},
        ]
        return RateCard.objects.create(
            metric_definition=m, pricing_model="tiered",
            tiered_pricing_json=tiers,
        )

    def test_usage_within_first_tier(self):
        org, proj, stack = self._make_org_project_stack()
        rc = self._create_tiered_rate_card()
        inv = Invoice.objects.create(
            organization=org, invoice_month="2026-03-01",
            subtotal_amount=0, tax_amount=0, total_amount=0,
        )
        item = InvoiceLineItem(
            invoice=inv, stack=stack, description="CPU",
            rate_card=rc, units_used=Decimal("50"), line_amount=Decimal("0"),
        )
        item.save()
        # 50 * 0.10 = 5.00
        self.assertEqual(item.line_amount, Decimal("5.00"))

    def test_usage_spanning_two_tiers(self):
        org, proj, stack = self._make_org_project_stack()
        rc = self._create_tiered_rate_card()
        inv = Invoice.objects.create(
            organization=org, invoice_month="2026-04-01",
            subtotal_amount=0, tax_amount=0, total_amount=0,
        )
        item = InvoiceLineItem(
            invoice=inv, stack=stack, description="CPU",
            rate_card=rc, units_used=Decimal("250"), line_amount=Decimal("0"),
        )
        item.save()
        # first 100 * 0.10 = 10.00, next 150 * 0.08 = 12.00 → 22.00
        self.assertEqual(item.line_amount, Decimal("22.00"))

    def test_usage_spanning_all_tiers(self):
        org, proj, stack = self._make_org_project_stack()
        rc = self._create_tiered_rate_card()
        inv = Invoice.objects.create(
            organization=org, invoice_month="2026-05-01",
            subtotal_amount=0, tax_amount=0, total_amount=0,
        )
        item = InvoiceLineItem(
            invoice=inv, stack=stack, description="CPU",
            rate_card=rc, units_used=Decimal("700"), line_amount=Decimal("0"),
        )
        item.save()
        # Band 1: 100 * 0.10 = 10, Band 2: 500 * 0.08 = 40, Band 3: 100 * 0.05 = 5 → 55
        self.assertEqual(item.line_amount, Decimal("55.00"))
