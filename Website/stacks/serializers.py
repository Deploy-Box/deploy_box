from rest_framework import serializers
from .models import StackDatabase, Stack, PurchasableStack


class StackDatabaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = StackDatabase
        fields = [
            "id",
            "stack",
            "uri",
            "created_at",
            "updated_at",
            "current_usage",
            "pending_billed",
        ]


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
            "iac",
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


class StackCreateSerializer(serializers.Serializer):
    project_id = serializers.CharField(max_length=100)
    purchasable_stack_id = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=100)


class StackUpdateSerializer(serializers.Serializer):
    root_directory = serializers.CharField(max_length=100, required=False)


class PurchasableStackCreateSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=10)
    variant = serializers.CharField(max_length=10)
    version = serializers.CharField(max_length=10)
    price_id = serializers.CharField(max_length=50)


class StackDatabaseUpdateSerializer(serializers.Serializer):
    data = serializers.JSONField()
