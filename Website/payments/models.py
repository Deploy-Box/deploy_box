from decimal import Decimal
from typing import Iterable
from django.core.exceptions import ValidationError
from django.db import models
from organizations.models import Organization
from stacks.models import Stack
from stacks.metrics.models import MetricDefinition


class RateCard(models.Model):
    metric_definition = models.ForeignKey(MetricDefinition, on_delete=models.CASCADE, related_name="rate_cards")
    pricing_model = models.CharField(max_length=50, choices=[('flat_rate', 'Flat Rate'), ('per_unit', 'Per Unit'), ('tiered', 'Tiered')])
    flat_rate_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    price_per_unit = models.DecimalField(max_digits=12, decimal_places=6, blank=True, null=True)
    tiered_pricing_json = models.JSONField(blank=True, null=True)  # e.g., [{"up_to": 1000, "price_per_unit": 0.10}, {"up_to": null, "price_per_unit": 0.08}]
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.pricing_model == 'flat_rate':
            return f"{self.metric_definition} @ Flat Rate ${self.flat_rate_price}"
        elif self.pricing_model == 'per_unit':
            return f"{self.metric_definition} @ ${self.price_per_unit} per unit"
        elif self.pricing_model == 'tiered':
            return f"{self.metric_definition} @ Tiered Pricing"
        
        return f"{self.metric_definition} @ Unknown Pricing Model"
    
    def save(self, *args, **kwargs):
        # Validate fields based on pricing model
        if self.pricing_model == 'flat_rate':
            if self.flat_rate_price is None:
                raise ValidationError("Flat rate price must be set for flat_rate pricing model")
            self.price_per_unit = None
            self.tiered_pricing_json = None
        elif self.pricing_model == 'per_unit':
            if self.price_per_unit is None:
                raise ValidationError("Price per unit must be set for per_unit pricing model")
            self.flat_rate_price = None
            self.tiered_pricing_json = None
        elif self.pricing_model == 'tiered':
            if self.tiered_pricing_json is None:
                raise ValidationError("Tiered pricing JSON must be set for tiered pricing model")

            # Ensure tiered_pricing_json is a list of dicts with 'up_to' and 'price_per_unit'
            if not isinstance(self.tiered_pricing_json, Iterable):
                raise ValidationError("Tiered pricing JSON must be an iterable")
            for tier in list(self.tiered_pricing_json or []):
                if 'up_to' not in tier or 'price_per_unit' not in tier:
                    raise ValidationError("Each tier must have 'up_to' and 'price_per_unit'")

            self.flat_rate_price = None
            self.price_per_unit = None

        return super().save(*args, **kwargs)


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

    subtotal_amount = models.DecimalField(max_digits=18, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2)

    issued_at = models.DateTimeField(blank=True, null=True)
    due_at = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_last_sync_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ("organization", "invoice_month")

    def __str__(self):
        return f"Invoice {self.invoice_month} - {self.organization.name}"

class InvoiceLineItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    stack = models.ForeignKey(Stack, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    rate_card = models.ForeignKey(RateCard, on_delete=models.SET_NULL, null=True, blank=True)
    units_used = models.DecimalField(max_digits=18, decimal_places=6)
    line_amount = models.DecimalField(max_digits=18, decimal_places=2)

    def __str__(self):
        return f"Line Item for {self.invoice} (${self.line_amount})"
    
    def save(self, *args, **kwargs):
        if self.rate_card:
            if self.rate_card.pricing_model == 'flat_rate':
                self.line_amount = self.rate_card.flat_rate_price

            elif self.rate_card.pricing_model == 'per_unit':
                if self.rate_card.price_per_unit is None:
                    raise ValidationError("Price per unit must be set for per_unit pricing model")
                self.line_amount = self.units_used * self.rate_card.price_per_unit
                
            elif self.rate_card.pricing_model == 'tiered':
                if self.rate_card.tiered_pricing_json is None:
                    raise ValidationError("Tiered pricing JSON must be set for tiered pricing model")
                total_units = self.units_used
                amount = Decimal("0")
                for tier in sorted(self.rate_card.tiered_pricing_json, key=lambda x: (x['up_to'] is None, x['up_to'] or float('inf'))):
                    tier_limit = tier['up_to']
                    tier_price = Decimal(str(tier['price_per_unit']))
                    if tier_limit is None or total_units <= tier_limit:
                        amount += total_units * tier_price
                        break
                    else:
                        amount += Decimal(str(tier_limit)) * tier_price
                        total_units -= tier_limit
                self.line_amount = amount

        return super().save(*args, **kwargs)
