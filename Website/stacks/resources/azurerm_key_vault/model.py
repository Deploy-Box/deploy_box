import os
from django.db import models

from core.fields import ShortUUIDField
from stacks.resources.base_resource_model import BaseResourceModel

CLASS_PREFIX = "res00D"
RESOURCE_NAME = "azurerm_key_vault"

class AzurermKeyVault(BaseResourceModel):
	id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)

	# Resource specific fields
	azurerm_id = models.CharField(max_length=255)
	azurerm_name = models.CharField(max_length=255)
	location = models.CharField(max_length=255, default='eastus')
	resource_group_name = models.CharField(max_length=255)
	tags = models.JSONField(default=dict, blank=True)
	sku_name = models.CharField(max_length=50, default='standard')
	soft_delete_retention_days = models.IntegerField(default=7)
	purge_protection_enabled = models.BooleanField(default=False)
	enabled_for_deployment = models.BooleanField(default=False)
	enabled_for_disk_encryption = models.BooleanField(default=False)
	enabled_for_template_deployment = models.BooleanField(default=False)
	enable_rbac_authorization = models.BooleanField(default=True)
	public_network_access_enabled = models.BooleanField(default=True)
	vault_uri = models.CharField(max_length=255, blank=True, default='')

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
