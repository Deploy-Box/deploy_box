from rest_framework import serializers
from organizations.models import Organization
from organizations.services import create_organization


class OrganizationSignupSerializer(serializers.Serializer):
    org_name = serializers.CharField()
    org_email = serializers.EmailField()

    def create(self, validated_data):
        user = self.context.get("user")
        if not user:
            raise ValueError("User must be provided in context")

        org = create_organization(
            user=user,
            name=validated_data["org_name"],
            email=validated_data["org_email"],
        )
        return org
