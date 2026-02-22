from rest_framework import serializers
from .models import Stack, PurchasableStack


class StackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stack
        fields = ["__all__"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PurchasableStackSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchasableStack
        fields = ["__all__"]
        read_only_fields = ["id", "created_at", "updated_at"]
