from rest_framework import serializers
from .model import AzurermPublicIp


class AzurermPublicIpSerializer(serializers.ModelSerializer):
	class Meta:
		model = AzurermPublicIp
		fields = '__all__'
		read_only_fields = ["id", "created_at", "updated_at"]
