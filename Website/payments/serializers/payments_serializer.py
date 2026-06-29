from rest_framework import serializers
from payments.models import Invoice


class InvoiceReadSerializer(serializers.ModelSerializer):
    """Read serializer for invoice data."""
    class Meta:
        model = Invoice
        fields = ["id", "organization", "invoice_month", "total_amount", "status", "created_at"]
        read_only_fields = fields


class PaymentIntentSerializer(serializers.Serializer):
    """Serializer for creating a payment intent / setup intent."""
    organization_id = serializers.CharField()


class SavePaymentMethodSerializer(serializers.Serializer):
    """Serializer for saving a payment method."""
    payment_method_id = serializers.CharField()
    organization_id = serializers.CharField()