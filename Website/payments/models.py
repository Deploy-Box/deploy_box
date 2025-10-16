from django.db import models
from django.db.models import Sum, Avg, Q, UniqueConstraint, Index
from django.utils import timezone
from decimal import Decimal
from core.fields import ShortUUIDField


# =========================
# Core / Reference Entities
# =========================

class Currency(models.TextChoices):
    USD = "USD", "USD"
    EUR = "EUR", "EUR"
    GBP = "GBP", "GBP"


class Account(models.Model):
    """
    Commercial 'account' for billing; tied 1:1 with your Organization for minimal refactor.
    """
    id = ShortUUIDField(primary_key=True)
    organization = models.OneToOneField(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='account',
    )
    name = models.CharField(max_length=200)
    email_billing = models.EmailField()
    currency = models.CharField(
        max_length=3, choices=Currency.choices, default=Currency.USD
    )
    created_at = models.DateTimeField(auto_now_add=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    id = ShortUUIDField(primary_key=True)
    code = models.SlugField(max_length=50, unique=True)  # e.g. compute, storage, api
    name = models.CharField(max_length=200)
    taxable = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


# =========================
# Pricing & Metering
# =========================

class PricePlan(models.Model):
    id = ShortUUIDField(primary_key=True)
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name='price_plans',
        null=True, blank=True  # null => public plan usable by many accounts
    )
    name = models.CharField(max_length=120)  # e.g., "Pro 2025-10"
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            Index(fields=['account', 'is_default']),
        ]

    def __str__(self):
        return f"{self.account or 'public'} · {self.name}"


class PriceComponentKind(models.TextChoices):
    RECURRING_FIXED = "RECURRING_FIXED", "Recurring Fixed"
    METERED = "METERED", "Metered"


class Meter(models.Model):
    """
    Registry of measurable things. meter_code referenced throughout (e.g., 'api_calls', 'gb_day', 'cpu_min').
    """
    code = models.SlugField(primary_key=True, max_length=60)
    description = models.TextField(blank=True, null=True)
    unit_name = models.CharField(max_length=40)  # 'call', 'GB-day', 'CPU-min'
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code


class PriceComponent(models.Model):
    id = ShortUUIDField(primary_key=True)
    price_plan = models.ForeignKey(
        PricePlan, on_delete=models.CASCADE, related_name='components'
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='components'
    )
    kind = models.CharField(max_length=20, choices=PriceComponentKind.choices)
    meter = models.ForeignKey(
        Meter, on_delete=models.PROTECT, null=True, blank=True, related_name='price_components'
    )
    unit_name = models.CharField(max_length=40)  # 'month' for recurring, else meter unit
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.USD)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(kind='METERED', meter__isnull=False) | Q(kind='RECURRING_FIXED'),
                name='pc_meter_required_for_metered',
            ),
        ]

    def __str__(self):
        tag = self.meter_id or "base"
        return f"{self.price_plan.name} · {self.product.code} · {self.kind} · {tag}"


class PriceTier(models.Model):
    id = ShortUUIDField(primary_key=True)
    price_component = models.ForeignKey(
        PriceComponent, on_delete=models.CASCADE, related_name='tiers'
    )
    start_qty = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('0'))
    end_qty = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)  # null => open-ended
    unit_price_cents = models.PositiveBigIntegerField()  # price per unit in this tier (in cents)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_qty']
        constraints = [
            models.CheckConstraint(
                check=Q(end_qty__isnull=True) | Q(end_qty__gt=models.F('start_qty')),
                name='pt_end_after_start'
            ),
        ]


# =========================
# Usage → Daily Rollups → Charges
# =========================

class UsageEvent(models.Model):
    """
    Raw usage events (append-only). Use this from services.
    """
    id = ShortUUIDField(primary_key=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='usage_events')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='usage_events')
    meter = models.ForeignKey(Meter, on_delete=models.PROTECT, related_name='usage_events')
    stack = models.ForeignKey('stacks.Stack', on_delete=models.PROTECT, related_name='usage_events', null=True, blank=True)

    quantity = models.DecimalField(max_digits=20, decimal_places=6)  # non-negative
    occurred_at = models.DateTimeField()            # when it happened
    received_at = models.DateTimeField(auto_now_add=True)  # when recorded
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        indexes = [
            Index(fields=['account', 'product', 'meter', 'occurred_at']),
        ]
        constraints = [
            models.CheckConstraint(check=Q(quantity__gte=0), name='ue_quantity_gte_0'),
        ]


class UsageDailyRollup(models.Model):
    """
    Summed per day for faster pricing & analytics.
    """
    id = ShortUUIDField(primary_key=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='usage_rollups')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='usage_rollups')
    meter = models.ForeignKey(Meter, on_delete=models.PROTECT, related_name='usage_rollups')
    usage_date = models.DateField()
    quantity = models.DecimalField(max_digits=20, decimal_places=6)

    class Meta:
        unique_together = [('account', 'product', 'meter', 'usage_date')]
        indexes = [
            Index(fields=['account', 'usage_date']),
        ]


class ChargeSource(models.TextChoices):
    USAGE = "USAGE", "Usage"
    RECURRING = "RECURRING", "Recurring"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"


class Charge(models.Model):
    """
    Materialized priced items; immutable once invoiced.
    """
    id = ShortUUIDField(primary_key=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='charges')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='charges')
    meter = models.ForeignKey(Meter, on_delete=models.PROTECT, null=True, blank=True, related_name='charges')
    source = models.CharField(max_length=12, choices=ChargeSource.choices)
    usage_date = models.DateField(null=True, blank=True)  # for daily usage charges

    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('1'))
    unit_name = models.CharField(max_length=40)

    unit_price_cents = models.BigIntegerField()   # signed for adjustments
    amount_cents = models.BigIntegerField()       # quantity * unit price (rounded by policy)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.USD)

    price_plan = models.ForeignKey(PricePlan, on_delete=models.SET_NULL, null=True, blank=True)
    price_component = models.ForeignKey(PriceComponent, on_delete=models.SET_NULL, null=True, blank=True)

    invoiced = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            Index(fields=['account', 'usage_date', 'invoiced']),
        ]


# =========================
# Invoices
# =========================

class InvoiceStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    OPEN = "OPEN", "Open"
    PAID = "PAID", "Paid"
    VOID = "VOID", "Void"


class Invoice(models.Model):
    id = ShortUUIDField(primary_key=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='invoices')
    period_start = models.DateField()
    period_end = models.DateField()
    issue_at = models.DateTimeField(default=timezone.now)
    due_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=8, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.USD)

    subtotal_cents = models.BigIntegerField(default=0)
    discount_cents = models.BigIntegerField(default=0)
    tax_cents = models.BigIntegerField(default=0)
    total_cents = models.BigIntegerField(default=0)

    notes = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            Index(fields=['account', 'period_start', 'period_end']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(total_cents__gte=0),
                name='invoice_total_nonnegative'
            ),
        ]


class InvoiceLine(models.Model):
    id = ShortUUIDField(primary_key=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    charge = models.ForeignKey(Charge, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice_lines')

    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('1'))
    unit_name = models.CharField(max_length=40)
    unit_price_cents = models.BigIntegerField()
    amount_cents = models.BigIntegerField()

    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    meter = models.ForeignKey(Meter, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        indexes = [
            Index(fields=['invoice']),
        ]


# =========================
# Discounts
# =========================

class DiscountKind(models.TextChoices):
    PERCENT = "PERCENT", "Percent"
    FIXED = "FIXED", "Fixed amount"


class DiscountScope(models.TextChoices):
    ALL = "ALL", "Entire invoice"
    PRODUCT = "PRODUCT", "Specific product"
    METER = "METER", "Specific meter"


class Discount(models.Model):
    id = ShortUUIDField(primary_key=True)
    code = models.SlugField(max_length=60, unique=True, null=True, blank=True)
    name = models.CharField(max_length=200)

    kind = models.CharField(max_length=10, choices=DiscountKind.choices)
    percent = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    fixed_cents = models.PositiveBigIntegerField(null=True, blank=True)

    scope = models.CharField(max_length=10, choices=DiscountScope.choices, default=DiscountScope.ALL)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    meter = models.ForeignKey(Meter, on_delete=models.CASCADE, null=True, blank=True)

    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    recurring = models.BooleanField(default=True)
    stackable = models.BooleanField(default=False)
    max_redemptions = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(Q(kind='PERCENT', percent__isnull=False, fixed_cents__isnull=True) |
                       Q(kind='FIXED', fixed_cents__isnull=False, percent__isnull=True)),
                name='discount_kind_fields_valid'
            ),
            models.CheckConstraint(
                check=Q(scope='ALL') |
                      Q(scope='PRODUCT', product__isnull=False) |
                      Q(scope='METER', meter__isnull=False),
                name='discount_scope_targets_valid'
            ),
        ]


class AccountDiscount(models.Model):
    id = ShortUUIDField(primary_key=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='account_discounts')
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name='account_links')
    redeemed_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = [('account', 'discount')]


class DiscountApplication(models.Model):
    """
    Audit of how discounts were applied to an invoice/line.
    """
    id = ShortUUIDField(primary_key=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='discount_applications')
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name='applications')
    invoice_line = models.ForeignKey(InvoiceLine, on_delete=models.SET_NULL, null=True, blank=True, related_name='discount_applications')
    amount_cents = models.PositiveBigIntegerField()


# =========================
# Wallet & Payments
# =========================

class Wallet(models.Model):
    account = models.OneToOneField(Account, on_delete=models.CASCADE, primary_key=True, related_name='wallet')
    balance_cents = models.BigIntegerField(default=0)  # can go negative if you allow overdraft
    updated_at = models.DateTimeField(auto_now=True)


class WalletTxKind(models.TextChoices):
    TOPUP = "TOPUP", "Top-up"
    DEBIT_INVOICE = "DEBIT_INVOICE", "Debit invoice"
    REFUND = "REFUND", "Refund"
    EXPIRY = "EXPIRY", "Expiry"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"


class WalletTransaction(models.Model):
    id = ShortUUIDField(primary_key=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='wallet_transactions')
    kind = models.CharField(max_length=20, choices=WalletTxKind.choices)
    amount_cents = models.BigIntegerField()  # positive = credit, negative = debit
    related_invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='wallet_transactions')
    external_ref = models.CharField(max_length=255, null=True, blank=True)  # PSP txn id, etc.
    expires_at = models.DateTimeField(null=True, blank=True)                # for promo credits
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            Index(fields=['account', 'created_at']),
        ]


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"


class Payment(models.Model):
    id = ShortUUIDField(primary_key=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='payments')
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    amount_cents = models.PositiveBigIntegerField()
    method = models.CharField(max_length=30)  # 'card', 'ach', 'wire', 'wallet'
    status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    external_ref = models.CharField(max_length=255, null=True, blank=True)  # PSP charge id
    created_at = models.DateTimeField(auto_now_add=True)


# =========================
# Convenience Query Helpers
# =========================

class UsageView(models.Manager):
    def total_current_for_org(self, organization):
        """
        Sum of yesterday's rollup for all meters/products. Adjust 'current' definition as needed.
        """
        today = timezone.localdate()
        return (UsageDailyRollup.objects
                .filter(account__organization=organization, usage_date=today)
                .aggregate(total=Sum('quantity'))['total'] or Decimal('0'))

    def month_totals_for_org(self, organization, year=None, month=None):
        if year is None:
            year = timezone.now().year
        if month is None:
            month = timezone.now().month
        return (UsageDailyRollup.objects
                .filter(account__organization=organization,
                        usage_date__year=year,
                        usage_date__month=month)
                .values('product__code', 'meter__code')
                .annotate(total=Sum('quantity'))
                .order_by('product__code', 'meter__code'))

    def trends_by_stack(self, organization, days=30):
        start_date = timezone.localdate() - timezone.timedelta(days=days)
        # Use raw events when you want per-stack shape; rollups can also include stack if you add it.
        return (UsageEvent.objects
                .filter(account__organization=organization, occurred_at__date__gte=start_date)
                .values('stack__name', 'meter__code', 'occurred_at__date')
                .annotate(daily=Sum('quantity'))
                .order_by('stack__name', 'meter__code', 'occurred_at__date'))


# Put helpers on Account for convenience
Account.add_to_class('usage', UsageView())


# ===============
# Stripe glue (optional, mirrors your existing fields)
# ===============

class BillingHistory(models.Model):
    """
    Optional: keep this if you want a simple view mirroring Stripe invoices.
    Prefer linking directly to Invoice + Payment for productized flows.
    """
    class BillingStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        OVERDUE = 'overdue', 'Overdue'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    id = ShortUUIDField(primary_key=True)
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='billing_history')
    amount_cents = models.PositiveBigIntegerField(default=0)   # switched to cents
    description = models.CharField(max_length=255, blank=True, null=True)
    billed_usage = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal('0'))
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, default=BillingStatus.PENDING, choices=BillingStatus.choices)
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_invoice_hosted_url = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Billing History"

    @classmethod
    def get_billing_history_for_organization(cls, organization):
        return cls.objects.filter(organization=organization).order_by('-created_at')

    @classmethod
    def get_organization_pending_total(cls, organization):
        return cls.objects.filter(
            organization=organization,
            status=cls.BillingStatus.PENDING
        ).aggregate(total_amount=Sum('amount_cents'))['total_amount'] or 0
