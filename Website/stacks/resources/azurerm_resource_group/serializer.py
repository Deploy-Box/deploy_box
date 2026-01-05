from rest_framework import serializers
from .model import AzurermResourceGroup


class AzurermResourceGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = AzurermResourceGroup
        fields = '__all__'
        read_only_fields = ["id", "created_at", "updated_at"]
