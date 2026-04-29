import os
from django.db import models

from core.fields import ShortUUIDField
from stacks.resources.base_resource_model import BaseResourceModel

CLASS_PREFIX = "res00F"
RESOURCE_NAME = "azurerm_public_ip"

class AzurermPublicIp(BaseResourceModel):
	id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)

	# Resource specific fields
	azurerm_id = models.CharField(max_length=255)
	azurerm_name = models.CharField(max_length=255)
	location = models.CharField(max_length=255, default='eastus')
	resource_group_name = models.CharField(max_length=255)
	allocation_method = models.CharField(max_length=50, default='Static')
	sku = models.CharField(max_length=50, default='Standard')
	ip_address = models.CharField(max_length=50, blank=True, default='')
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
