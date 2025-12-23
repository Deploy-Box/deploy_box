from rest_framework import serializers
from .model import AzurermResourceGroup


class AzurermResourceGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = AzurermResourceGroup
        fields = [
            "id",
            "name",
            "stack",
            "type",
            "azurerm_id",
            "azurerm_name",
            "location",
            "tags",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
