import os
from django.db import models

from core.fields import ShortUUIDField
from stacks.resources.base_resource_model import BaseResourceModel

CLASS_PREFIX = "res000"
RESOURCE_NAME = "azurerm_resource_group"

class AzurermResourceGroup(BaseResourceModel):
	id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)

	# Resource specific fields
	azurerm_id = models.CharField(max_length=255)
	azurerm_name = models.CharField(max_length=255)
	location = models.CharField(max_length=255, default='eastus')
	tags = models.JSONField(default=dict, blank=True)

	def save(self, *args, **kwargs):
		environment = os.getenv('ENV', 'DEV').lower()
		self.name = f"{RESOURCE_NAME}_{self.index}"
		if environment == 'prod':
			self.azurerm_name = f"{CLASS_PREFIX}_{self.index}_{self.stack.pk}"
		else:
			self.azurerm_name = f"{CLASS_PREFIX}_{self.index}_{self.stack.pk}_{environment}"

		super().save(*args, **kwargs)
