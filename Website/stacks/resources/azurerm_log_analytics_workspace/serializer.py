from rest_framework import serializers
from .model import AzurermLogAnalyticsWorkspace


class AzurermLogAnalyticsWorkspaceSerializer(serializers.ModelSerializer):
	class Meta:
		model = AzurermLogAnalyticsWorkspace
		fields = '__all__'
		read_only_fields = ["id", "created_at", "updated_at"]
