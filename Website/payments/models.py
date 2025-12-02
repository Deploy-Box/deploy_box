from django.db import models
from organizations.models import Organization
from stacks.models import Stack


# Defines a pricing plan that determines cost per usage unit.
class SKU(models.Model):
    name = models.CharField(max_length=255)
    currency = models.CharField(max_length=10, default="USD")
    unit_name = models.CharField(max_length=50)  # e.g., "stack-day", "vCPU-hour"
    price_per_unit = models.DecimalField(max_digits=12, decimal_places=6)
    billing_cycle = models.CharField(max_length=50, default="monthly")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.currency})"


class DailyUsage(models.Model):
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE, related_name="daily_usage")
    usage_date = models.DateField()
    units_used = models.DecimalField(max_digits=18, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("stack", "usage_date")

    def __str__(self):
        return f"{self.stack} - {self.usage_date}: {self.units_used}"


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('void', 'Void'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="invoices")
    invoice_month = models.DateField()  # usually use the first of the month
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    currency = models.CharField(max_length=10, default="USD")

    subtotal_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    issued_at = models.DateTimeField(blank=True, null=True)
    due_at = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ("organization", "invoice_month")

    def __str__(self):
        return f"Invoice {self.invoice_month} - {self.organization.name}"

class InvoiceLineItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    stack = models.ForeignKey(Stack, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()

    units_used = models.DecimalField(max_digits=18, decimal_places=6)
    unit_price = models.DecimalField(max_digits=12, decimal_places=6)
    line_amount = models.DecimalField(max_digits=18, decimal_places=2)

    def __str__(self):
        return f"Line Item for {self.invoice} (${self.line_amount})"
