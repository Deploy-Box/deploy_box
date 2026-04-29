from rest_framework import serializers
from .model import AzurermNetworkSecurityGroup


class AzurermNetworkSecurityGroupSerializer(serializers.ModelSerializer):
	class Meta:
		model = AzurermNetworkSecurityGroup
		fields = '__all__'
		read_only_fields = ["id", "created_at", "updated_at"]
