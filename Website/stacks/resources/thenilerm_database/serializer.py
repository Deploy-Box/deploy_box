from rest_framework import serializers
from .model import TheNilermDatabase


class TheNilermDatabaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TheNilermDatabase
        fields = '__all__'
        read_only_fields = ["id", "created_at", "updated_at"]
