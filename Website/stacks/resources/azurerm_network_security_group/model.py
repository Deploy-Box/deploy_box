import os
from django.db import models

from core.fields import ShortUUIDField
from stacks.resources.base_resource_model import BaseResourceModel

CLASS_PREFIX = "res010"
RESOURCE_NAME = "azurerm_network_security_group"

class AzurermNetworkSecurityGroup(BaseResourceModel):
	id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)

	# Resource specific fields
	azurerm_id = models.CharField(max_length=255)
	azurerm_name = models.CharField(max_length=255)
	location = models.CharField(max_length=255, default='eastus')
	resource_group_name = models.CharField(max_length=255)
	security_rules = models.JSONField(default=list, blank=True)
	tags = models.JSONField(default=dict, blank=True)

	def __str__(self):
		return self.name

	def save(self, *args, **kwargs):
		assert self.stack is not None, "Stack must be provided"
		assert isinstance(self.stack, models.Model), "Stack must be a valid Stack instance"
		environment = os.getenv('ENV', 'DEV').lower()
		self.name = f"{RESOURCE_NAME}_{self.index}"
		if environment == 'prod':
			self.azurerm_name = f"{CLASS_PREFIX}-{self.index}-{self.stack.pk}"
		else:
			self.azurerm_name = f"{CLASS_PREFIX}-{self.index}-{self.stack.pk}-{environment}"

		super().save(*args, **kwargs)
