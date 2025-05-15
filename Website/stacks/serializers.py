from rest_framework import serializers
from .models import StackDatabase


class StackDatabaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = StackDatabase
        fields = [
            "id",
            "stack",
            "uri",
            "created_at",
            "updated_at",
            "current_usage",
            "pending_billed",
        ]
