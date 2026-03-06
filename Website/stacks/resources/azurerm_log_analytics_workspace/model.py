import os
from django.db import models

from core.fields import ShortUUIDField
from stacks.resources.base_resource_model import BaseResourceModel

CLASS_PREFIX = "res00C"
RESOURCE_NAME = "azurerm_log_analytics_workspace"

class AzurermLogAnalyticsWorkspace(BaseResourceModel):
	id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)

	# Resource specific fields
	azurerm_id = models.CharField(max_length=255)
	azurerm_name = models.CharField(max_length=255)
	location = models.CharField(max_length=255, default='eastus')
	resource_group_name = models.CharField(max_length=255)
	tags = models.JSONField(default=dict, blank=True)
	sku = models.CharField(max_length=50, default='PerGB2018')
	retention_in_days = models.IntegerField(default=30)
	daily_quota_gb = models.FloatField(default=-1)
	internet_ingestion_enabled = models.BooleanField(default=True)
	internet_query_enabled = models.BooleanField(default=True)
	primary_shared_key = models.CharField(max_length=255, blank=True, default='')
	secondary_shared_key = models.CharField(max_length=255, blank=True, default='')
	workspace_id = models.CharField(max_length=255, blank=True, default='')

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
