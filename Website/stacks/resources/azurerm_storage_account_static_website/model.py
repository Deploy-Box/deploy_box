import os
from django.db import models

from core.fields import ShortUUIDField
from stacks.resources.base_resource_model import BaseResourceModel

CLASS_PREFIX = "res00A"
RESOURCE_NAME = "azurerm_storage_account_static_website"

class AzurermStorageAccountStaticWebsite(BaseResourceModel):
	id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)

	# Resource specific fields
	azurerm_id = models.CharField(max_length=255)
	azurerm_name = models.CharField(max_length=255)
	storage_account_id = models.CharField(max_length=255)
	error_404_document = models.CharField(max_length=255, default='404.html')
	index_document = models.CharField(max_length=255, default='index.html')
	static_file_directory = models.CharField(max_length=255, default='')
	static_file_build_command = models.CharField(max_length=255, default='')
	static_file_build_output_directory = models.CharField(max_length=255, default='')

	def save(self, *args, **kwargs):
		environment = os.getenv('ENV', 'DEV').lower()
		self.name = f"{RESOURCE_NAME}_{self.index}"
		if environment == 'prod':
			self.azurerm_name = f"{CLASS_PREFIX}_{self.index}_{self.stack.pk}"
		else:
			self.azurerm_name = f"{CLASS_PREFIX}_{self.index}_{self.stack.pk}_{environment}"

		super().save(*args, **kwargs)
