from rest_framework import serializers
from .model import DeployBoxrmWorkOSIntegration


class DeployBoxrmWorkosIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeployBoxrmWorkOSIntegration
        fields = '__all__'
        read_only_fields = ["id", "created_at", "updated_at"]
