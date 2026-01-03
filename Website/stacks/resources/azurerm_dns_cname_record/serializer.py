from rest_framework import serializers
from .model import AzurermDnsCnameRecord


class AzurermDnsCnameRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AzurermDnsCnameRecord
        fields = '__all__'
        read_only_fields = ["id", "created_at", "updated_at"]
