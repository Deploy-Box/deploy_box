from rest_framework import serializers
from .model import AzurermNetworkInterface


class AzurermNetworkInterfaceSerializer(serializers.ModelSerializer):
	class Meta:
		model = AzurermNetworkInterface
		fields = '__all__'
		read_only_fields = ["id", "created_at", "updated_at"]
