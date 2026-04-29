from rest_framework import serializers
from .model import AzurermKeyVault


class AzurermKeyVaultSerializer(serializers.ModelSerializer):
	class Meta:
		model = AzurermKeyVault
		fields = '__all__'
		read_only_fields = ["id", "created_at", "updated_at"]
