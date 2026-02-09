from rest_framework import serializers
from .model import DeployBoxrmEdge


class DeployBoxrmEdgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeployBoxrmEdge
        fields = '__all__'
        read_only_fields = ["id", "created_at", "updated_at"]
