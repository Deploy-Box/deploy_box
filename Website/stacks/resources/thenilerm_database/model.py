import os
from django.db import models

from core.fields import ShortUUIDField
from stacks.resources.base_resource_model import BaseResourceModel

CLASS_PREFIX = "res009"
RESOURCE_NAME = "thenilerm_database"

class TheNilermDatabase(BaseResourceModel):
	id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)

	# Resource specific fields (updated for The Nile)
	thenilerm_id = models.CharField(max_length=255)
	thenilerm_name = models.CharField(max_length=255)
	status = models.CharField(max_length=32)
	region = models.CharField(max_length=64, default='AZURE_EASTUS')
	expandable = models.BooleanField(default=False)
	created = models.DateTimeField(null=True, blank=True)
	deleted = models.DateTimeField(null=True, blank=True)
	api_host = models.URLField(max_length=255)
	db_host = models.CharField(max_length=255)
	sharded = models.BooleanField(default=True)
	connection_string = models.TextField(null=True, blank=True)
	credential_id = models.CharField(max_length=255)
	credential_tenant = models.CharField(max_length=255, blank=True, null=True)
	credential_internal = models.BooleanField(default=False)
	credential_password = models.CharField(max_length=255)
	credential_created = models.DateTimeField(blank=True, null=True)

	def __str__(self):
		return f"thenilerm_database.{self.name}"

	def save(self, *args, **kwargs):
		assert self.stack is not None, "Stack must be provided"
		assert isinstance(self.stack, models.Model), "Stack must be a valid Stack instance"
		environment = os.getenv('ENV', 'DEV').lower()
		self.name = f"{RESOURCE_NAME}_{self.index}"
		if environment == 'prod':
			self.thenilerm_name = f"{CLASS_PREFIX}_{self.index}_{self.stack.pk}"
		else:
			self.thenilerm_name = f"{CLASS_PREFIX}_{self.index}_{self.stack.pk}_{environment}"
		super().save(*args, **kwargs)
