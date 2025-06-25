from rest_framework import serializers
from accounts.models import UserProfile
from django.contrib.auth.password_validation import validate_password
from django.db import transaction


class UserCreationSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "username",
            "email",
            "password1",
            "password2",
            "first_name",
            "last_name",
        ]

    def validate(self, data):
        if data["password1"] != data["password2"]:
            raise serializers.ValidationError({"password": "Passwords must match."})
        return data

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password1")
        user = UserProfile.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user
