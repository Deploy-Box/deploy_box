from rest_framework import serializers
from projects.models import Project


class ProjectReadSerializer(serializers.ModelSerializer):
    """Read serializer for project list/detail responses."""
    class Meta:
        model = Project
        fields = ["id", "name", "description", "created_at", "updated_at"]
        read_only_fields = fields


class ProjectCreateSerializer(serializers.Serializer):
    """Write serializer for project creation."""
    name = serializers.CharField(max_length=255)
    description = serializers.CharField()
    organization = serializers.CharField(help_text="Organization ID")
