from rest_framework import serializers
from ..models import Stack, StackDatabase


class StackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stack
        depth = 1
        fields = "__all__"


class StackDatabaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = StackDatabase
        depth = 2
        fields = "__all__"
