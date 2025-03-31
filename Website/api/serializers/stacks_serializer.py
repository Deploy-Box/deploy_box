from rest_framework import serializers
from ..models import Stacks, StackDatabases


class StacksSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stacks

        depth = 1
        fields = "__all__"


class StackDatabasesSerializer(serializers.ModelSerializer):
    class Meta:
        model = StackDatabases

        depth = 2
        fields = "__all__"
