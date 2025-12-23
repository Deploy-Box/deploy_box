from rest_framework import serializers
from .model import AzurermStorageAccount


class AzurermStorageAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = AzurermStorageAccount
        fields = '__all__'
        read_only_fields = ["id", "created_at", "updated_at"]
