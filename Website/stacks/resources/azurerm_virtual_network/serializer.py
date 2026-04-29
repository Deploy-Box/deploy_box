from rest_framework import serializers
from .model import AzurermVirtualNetwork


class AzurermVirtualNetworkSerializer(serializers.ModelSerializer):
	class Meta:
		model = AzurermVirtualNetwork
		fields = '__all__'
		read_only_fields = ["id", "created_at", "updated_at"]
