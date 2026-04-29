from rest_framework import serializers
from .model import DeployBoxrmPostgresDatabase


class DeployBoxrmPostgresDatabaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeployBoxrmPostgresDatabase
        fields = '__all__'
        read_only_fields = ["id", "created_at", "updated_at"]
