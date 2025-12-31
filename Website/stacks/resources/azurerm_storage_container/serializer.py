from rest_framework import serializers
from .model import AzurermStorageContainer


class AzurermStorageContainerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AzurermStorageContainer
        fields = '__all__'
        read_only_fields = ["id", "created_at", "updated_at"]
