from rest_framework import serializers
from .models import Stack, PurchasableStack


class StackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stack
        fields = [
            "id",
            "name",
            "project",
            "purchased_stack",
            "root_directory",
            "instance_usage",
            "instance_usage_bill_amount",
            "iac_state",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PurchasableStackSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchasableStack
        fields = [
            "id",
            "type",
            "variant",
            "version",
            "price_id",
            "description",
            "name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PurchasableStackCreateSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=10)
    variant = serializers.CharField(max_length=10)
    version = serializers.CharField(max_length=10)
    price_id = serializers.CharField(max_length=50)
