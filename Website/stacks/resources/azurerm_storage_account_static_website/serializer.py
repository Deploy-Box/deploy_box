from rest_framework import serializers
from .model import AzurermStorageAccountStaticWebsite


class AzurermStorageAccountStaticWebsiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AzurermStorageAccountStaticWebsite
        fields = '__all__'
        read_only_fields = ["id", "created_at", "updated_at"]
