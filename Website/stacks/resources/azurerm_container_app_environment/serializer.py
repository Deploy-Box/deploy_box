from rest_framework import serializers
from .model import AzurermContainerAppEnvironment


class AzurermContainerAppEnvironmentSerializer(serializers.ModelSerializer):
	class Meta:
		model = AzurermContainerAppEnvironment
		fields = '__all__'
		read_only_fields = ["id", "created_at", "updated_at"]
