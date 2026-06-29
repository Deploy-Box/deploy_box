from rest_framework import serializers
from accounts.models import UserProfile


class UserProfileReadSerializer(serializers.ModelSerializer):
    """Read-only serializer for user profile responses."""
    class Meta:
        model = UserProfile
        fields = ["id", "username", "email", "first_name", "last_name"]
        read_only_fields = fields


class UserProfileUpdateSerializer(serializers.Serializer):
    """Write serializer for profile updates — validates uniqueness."""
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
