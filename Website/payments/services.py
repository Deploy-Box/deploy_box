"""
Payments service layer — Stripe operations and billing logic.

Returns plain data (dicts) or raises ServiceError exceptions.
Never imports Response, JsonResponse, or HttpResponse.
"""
import logging
import random
import calendar
from datetime import date, timedelta
from decimal import Decimal

import stripe
from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from organizations.models import Organization
from payments.models import Invoice, InvoiceLineItem, RateCard

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


class NotFoundError(ServiceError):
    def __init__(self, message="Not found"):
        super().__init__(message, status_code=404)


# ── Stripe Customer ─────────────────────────────────────────────────────────

def create_stripe_customer(name: str, email: str) -> str:
    """Create a new customer in Stripe. Returns the Stripe customer ID."""
    customer = stripe.Customer.create(
        name=name,
        email=email,
        idempotency_key=f"create-customer-{email}",
    )
    return customer.id


def organization_has_payment_method(organization) -> bool:
    """Return True if the organization has at least one card on file in Stripe."""
    if not organization.stripe_customer_id:
        return False
    try:
        methods = stripe.PaymentMethod.list(
            customer=organization.stripe_customer_id,
            type="card",
        )
        return bool(methods.data)
    except stripe.error.StripeError:
        return False


def ensure_stripe_customer(organization: Organization) -> str:
    """Ensure the organization has a Stripe customer ID. Creates one if missing."""
    if not organization.stripe_customer_id:
        with transaction.atomic():
            customer = stripe.Customer.create(
                email=organization.email,
                name=organization.name,
                metadata={"organization_id": str(organization.id)},
                idempotency_key=f"ensure-customer-{organization.id}",
            )
            organization.stripe_customer_id = customer.id
            organization.save()
    return organization.stripe_customer_id


# ── Payment Methods ──────────────────────────────────────────────────────────

def get_all_payment_methods(customer_id: str) -> list[dict]:
    """Get all card payment methods for a Stripe customer."""
    payment_methods = stripe.PaymentMethod.list(customer=customer_id, type="card")
    customer = stripe.Customer.retrieve(customer_id)
    default_pm_id = (
        customer.invoice_settings.default_payment_method
        if customer.invoice_settings
        else None
    )

    return [
        {
            "id": pm.id,
            "brand": pm.card.brand,
            "last4": pm.card.last4,
            "exp_month": pm.card.exp_month,
            "exp_year": pm.card.exp_year,
            "is_default": pm.id == default_pm_id,
        }
        for pm in payment_methods.data
        if pm.card
    ]


def save_payment_method(payment_method_id: str, customer_id: str) -> dict:
    """Attach a payment method and set it as default."""
    stripe.PaymentMethod.attach(
        payment_method_id,
        customer=customer_id,
        idempotency_key=f"attach-pm-{payment_method_id}-{customer_id}",
    )
    stripe.Customer.modify(
        customer_id,
        invoice_settings={"default_payment_method": payment_method_id},
    )
    return {"message": "Payment method saved successfully."}


def set_default_payment_method(payment_method_id: str, customer_id: str) -> dict:
    """Set an existing payment method as the default."""
    payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
    if not payment_method or payment_method.customer != customer_id:
        raise NotFoundError("Payment method not found or doesn't belong to this customer")

    stripe.Customer.modify(
        customer_id,
        invoice_settings={"default_payment_method": payment_method_id},
    )
    return {"message": "Default payment method updated successfully."}


# ── Invoice ──────────────────────────────────────────────────────────────────

def create_invoice(customer_id: str, dollar_amount: float, description: str, idempotency_key: str | None = None):
    """Create and finalize a Stripe invoice. Returns (invoice_id, hosted_url) or None."""
    # Build a deterministic key from the operation inputs if none provided
    base_key = idempotency_key or f"invoice-{customer_id}-{int(100 * dollar_amount)}-{description}"
    try:
        stripe.InvoiceItem.create(
            customer=customer_id,
            amount=int(100 * dollar_amount),
            currency="usd",
            description=description,
            idempotency_key=f"{base_key}-item",
        )
        invoice = stripe.Invoice.create(
            customer=customer_id,
            auto_advance=False,
            idempotency_key=f"{base_key}-inv",
        )
        invoice.finalize_invoice()
        return invoice.id, invoice.hosted_invoice_url
    except Exception as e:
        logger.error("Error creating invoice: %s", e)
        return None


# ── Usage Data ───────────────────────────────────────────────────────────────

def get_usage_data(organization: Organization) -> dict:
    """Calculate usage statistics for an organization."""
    from stacks.models import Stack
    from stacks.metrics.models import MetricUsageRecord

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    days_elapsed = now.day

    org_stacks = Stack.objects.filter(project__organization=organization)

    daily_agg = MetricUsageRecord.objects.filter(
        stack__in=org_stacks, usage_datetime__gte=today_start,
    ).aggregate(total=Sum("amount_used"))
    current_daily_usage = daily_agg["total"] or Decimal("0.00")

    month_agg = MetricUsageRecord.objects.filter(
        stack__in=org_stacks, usage_datetime__gte=month_start,
    ).aggregate(total=Sum("amount_used"))
    current_usage = month_agg["total"] or Decimal("0.00")

    projected = (current_usage / days_elapsed) * days_in_month if days_elapsed > 0 else Decimal("0.00")

    draft_invoice = Invoice.objects.filter(
        organization=organization, invoice_month=month_start.date(), status="draft",
    ).first()
    actual_monthly_cost = draft_invoice.total_amount if draft_invoice else Decimal("0.00")

    return {
        "current_daily_usage": f"{current_daily_usage:.2f}",
        "current_usage": f"{current_usage:.2f}",
        "projected_monthly_usage": f"{projected:.2f}",
        "actual_monthly_cost": f"{actual_monthly_cost:.2f}",
        "month_start_formatted": month_start.strftime("%b 1, %Y"),
    }


def get_billing_history(organization: Organization) -> list[dict]:
    """Get billing history records for an organization."""
    invoices = Invoice.objects.filter(
        organization=organization,
    ).order_by("-invoice_month")

    return [
        {
            "created_at": inv.invoice_month.isoformat(),
            "description": f"Monthly usage - {inv.invoice_month.strftime('%B %Y')}",
            "amount": str(inv.total_amount),
            "status": inv.get_status_display(),
            "stripe_invoice_hosted_url": "",
        }
        for inv in invoices
    ]


# ── Monthly Invoice Generation ───────────────────────────────────────────────

def generate_monthly_invoices(billing_month: date = None) -> list[dict]:
    """Generate draft invoices for all organizations for the given month.

    Args:
        billing_month: First day of the month to bill. Defaults to previous month.

    Returns:
        List of dicts with invoice generation results per organization.
    """
    from stacks.models import Stack
    from stacks.metrics.models import MetricUsageRecord

    if billing_month is None:
        today = date.today()
        first_of_current = today.replace(day=1)
        billing_month = (first_of_current - timedelta(days=1)).replace(day=1)

    month_start = billing_month
    days_in_month = calendar.monthrange(billing_month.year, billing_month.month)[1]
    month_end = billing_month.replace(day=days_in_month)

    # Find organizations with usage in this billing period
    org_ids = (
        MetricUsageRecord.objects.filter(
            usage_datetime__date__gte=month_start,
            usage_datetime__date__lte=month_end,
        )
        .values_list("stack__project__organization", flat=True)
        .distinct()
    )
    organizations = Organization.objects.filter(id__in=org_ids)

    results = []
    for org in organizations:
        result = {"organization": org.name, "organization_id": str(org.id)}
        try:
            with transaction.atomic():
                # Get or create a draft invoice for this org + month
                invoice, created = Invoice.objects.update_or_create(
                    organization=org,
                    invoice_month=month_start,
                    defaults={
                        "status": "draft",
                        "subtotal_amount": Decimal("0.00"),
                        "tax_amount": Decimal("0.00"),
                        "total_amount": Decimal("0.00"),
                    },
                )

                # Delete existing line items so re-runs are idempotent
                invoice.line_items.all().delete()

                # Get all stacks belonging to this org
                org_stacks = Stack.objects.filter(project__organization=org)

                # Query usage records within the billing period grouped by stack + metric
                usage_groups = (
                    MetricUsageRecord.objects.filter(
                        stack__in=org_stacks,
                        usage_datetime__date__gte=month_start,
                        usage_datetime__date__lte=month_end,
                    )
                    .values("stack", "metric_definition")
                    .annotate(total_used=Sum("amount_used"))
                )

                line_items_created = 0
                for group in usage_groups:
                    stack_id = group["stack"]
                    metric_def_id = group["metric_definition"]
                    total_used = group["total_used"] or Decimal("0")

                    # Find matching rate card
                    rate_card = RateCard.objects.filter(
                        metric_definition_id=metric_def_id
                    ).first()
                    if not rate_card:
                        logger.warning(
                            "No RateCard for metric_definition_id=%s (org=%s). Skipping.",
                            metric_def_id,
                            org.name,
                        )
                        continue

                    InvoiceLineItem.objects.create(
                        invoice=invoice,
                        stack_id=stack_id,
                        rate_card=rate_card,
                        description=f"{rate_card.metric_definition.name} usage",
                        units_used=total_used,
                        line_amount=Decimal("0"),  # save() auto-calculates from rate_card
                    )
                    line_items_created += 1

                # Sum line items to compute totals
                subtotal = (
                    invoice.line_items.aggregate(total=Sum("line_amount"))["total"]
                    or Decimal("0.00")
                )
                tax_amount = Decimal("0.00")
                total_amount = subtotal + tax_amount

                invoice.subtotal_amount = subtotal
                invoice.tax_amount = tax_amount
                invoice.total_amount = total_amount
                invoice.save()

            # Stripe sync (outside the atomic block to avoid holding the txn)
            if org.stripe_customer_id and total_amount > 0:
                try:
                    description = f"Deploy Box - {billing_month.strftime('%B %Y')} usage"
                    stripe_result = create_invoice(
                        org.stripe_customer_id,
                        float(total_amount),
                        description,
                    )
                    if stripe_result:
                        stripe_invoice_id, _ = stripe_result
                        invoice.stripe_invoice_id = stripe_invoice_id
                        invoice.stripe_last_sync_date = timezone.now()
                        invoice.save(update_fields=["stripe_invoice_id", "stripe_last_sync_date"])
                        result["stripe_invoice_id"] = stripe_invoice_id
                except Exception as e:
                    logger.error("Stripe sync failed for org %s: %s", org.name, e)
                    result["stripe_error"] = str(e)

            result["status"] = "success"
            result["invoice_id"] = invoice.id
            result["line_items"] = line_items_created
            result["total_amount"] = str(total_amount)

        except Exception as e:
            logger.error("Invoice generation failed for org %s: %s", org.name, e)
            result["status"] = "error"
            result["error"] = str(e)

        results.append(result)

    return results


# ── Webhook Helpers ──────────────────────────────────────────────────────────

STACK_NAME_ADJECTIVES = [
    "Superb", "Incredible", "Fantastic", "Amazing", "Awesome", "Brilliant",
    "Exceptional", "Outstanding", "Remarkable", "Extraordinary", "Magnificent",
    "Spectacular", "Stunning", "Impressive",
]

STACK_NAME_NOUNS = [
    "Stack", "Project", "Application", "Service", "Solution", "Platform",
    "System", "Framework", "Architecture", "Design", "Model", "Structure",
    "Configuration",
]


def generate_random_stack_name() -> str:
    """Generate a fun random name for a newly purchased stack."""
    return f"{random.choice(STACK_NAME_ADJECTIVES)} {random.choice(STACK_NAME_NOUNS)}"