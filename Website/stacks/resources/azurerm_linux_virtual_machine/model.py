import os
from django.db import models

from core.fields import ShortUUIDField
from stacks.resources.base_resource_model import BaseResourceModel

CLASS_PREFIX = "res013"
RESOURCE_NAME = "azurerm_linux_virtual_machine"

class AzurermLinuxVirtualMachine(BaseResourceModel):
	id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)

	# Resource specific fields
	azurerm_id = models.CharField(max_length=255)
	azurerm_name = models.CharField(max_length=255)
	location = models.CharField(max_length=255, default='eastus')
	resource_group_name = models.CharField(max_length=255)
	size = models.CharField(max_length=100, default='Standard_B2s')
	admin_username = models.CharField(max_length=100, default='azureuser')
	admin_ssh_key_public_key = models.TextField(blank=True, default='')
	disable_password_authentication = models.BooleanField(default=True)
	network_interface_ids = models.JSONField(default=list, blank=True)

	# OS disk
	os_disk_caching = models.CharField(max_length=50, default='ReadWrite')
	os_disk_storage_account_type = models.CharField(max_length=50, default='Standard_LRS')

	# Source image reference
	source_image_publisher = models.CharField(max_length=255, default='Canonical')
	source_image_offer = models.CharField(max_length=255, default='ubuntu-24_04-lts')
	source_image_sku = models.CharField(max_length=255, default='server')
	source_image_version = models.CharField(max_length=255, default='latest')

	# State outputs
	private_ip_address = models.CharField(max_length=50, blank=True, default='')
	public_ip_address = models.CharField(max_length=50, blank=True, default='')

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
