from rest_framework import serializers
from .model import AzurermContainerApp


class AzurermContainerAppSerializer(serializers.ModelSerializer):
    class Meta:
        model = AzurermContainerApp
        fields = [
            "id",
            "name",
            "type",
            "azurerm_id",
            "azurerm_name",
            "resource_group_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
