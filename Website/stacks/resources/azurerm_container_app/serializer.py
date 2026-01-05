from rest_framework import serializers
from .model import AzurermContainerApp


class AzurermContainerAppSerializer(serializers.ModelSerializer):
    class Meta:
        model = AzurermContainerApp
        fields = '__all__'
        read_only_fields = ["id", "created_at", "updated_at"]
