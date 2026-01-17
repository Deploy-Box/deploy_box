import os
from django.db import models

from core.fields import ShortUUIDField
from stacks.resources.base_resource_model import BaseResourceModel

CONTAINER_ACCESS_TYPE_CHOICES = [
	('private', 'Private'),
	('blob', 'Blob'),
	('container', 'Container'),
]

CLASS_PREFIX = "res003"
RESOURCE_NAME = "azurerm_storage_container"

class AzurermStorageContainer(BaseResourceModel):
	id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)

	# Resource specific fields
	azurerm_id = models.CharField(max_length=255)
	azurerm_name = models.CharField(max_length=255)
	storage_account_id = models.CharField(max_length=255)
	container_access_type = models.CharField(max_length=50, choices=CONTAINER_ACCESS_TYPE_CHOICES, default='private')
	default_encryption_scope = models.CharField(max_length=255, blank=True, default='')
	encryption_scope_override_enabled = models.BooleanField(default=True)

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