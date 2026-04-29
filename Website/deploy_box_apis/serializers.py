from rest_framework import serializers


class ProjectIDSerializer(serializers.Serializer):
    """Common serializer for endpoints that require a project_id."""
    project_id = serializers.CharField()


class APIKeyCreateSerializer(serializers.Serializer):
    """Serializer for creating a new public API key."""
    project_id = serializers.CharField()
    name = serializers.CharField(default="Default", required=False)


class APIKeyRevokeSerializer(serializers.Serializer):
    """Serializer for revoking a public API key."""
    key_id = serializers.CharField()
    project_id = serializers.CharField()


class APIKeyValidateSerializer(serializers.Serializer):
    """Serializer for validating a public API key."""
    api_key = serializers.CharField()


class IncrementUsageSerializer(serializers.Serializer):
    """Serializer for the nested usage increment payload."""
    client_id = serializers.CharField()
    api_id = serializers.CharField()
