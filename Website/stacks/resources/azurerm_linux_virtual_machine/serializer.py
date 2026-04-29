from rest_framework import serializers
from .model import AzurermLinuxVirtualMachine


class AzurermLinuxVirtualMachineSerializer(serializers.ModelSerializer):
	class Meta:
		model = AzurermLinuxVirtualMachine
		fields = '__all__'
		read_only_fields = ["id", "created_at", "updated_at"]
