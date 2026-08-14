from django.contrib import admin
from payments.models import RateCard, Invoice, InvoiceLineItem


class RateCardAdmin(admin.ModelAdmin):
    list_display = ("metric_definition", "pricing_model", "flat_rate_price", "price_per_unit", "created_at")
    list_filter = ("pricing_model",)


class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("organization", "invoice_month", "status", "total_amount", "currency", "issued_at", "paid_at")
    list_filter = ("status", "currency", "invoice_month")


class InvoiceLineItemAdmin(admin.ModelAdmin):
    list_display = ("invoice", "stack", "description", "units_used", "line_amount")
    list_filter = ("invoice__status",)
