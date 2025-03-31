from rest_framework import serializers
from accounts.models import UserProfile


class PaymentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile

        depth = 1
        fields = "__all__"