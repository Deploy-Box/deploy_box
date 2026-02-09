from django.db import models

from core.fields import ShortUUIDField
from stacks.resources.base_resource_model import BaseResourceModel

CLASS_PREFIX = "res008"
RESOURCE_NAME = "deployboxrm_workos_integration"

class DeployBoxrmWorkOSIntegration(BaseResourceModel):
	id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)

	# Resource specific fields
	api_key = models.CharField(max_length=255)
	client_id = models.CharField(max_length=255)
	redirect_uri = models.CharField(max_length=255)

	def __str__(self):
		return f"{RESOURCE_NAME}.{self.name}"
    
	def save(self, *args, **kwargs):
		assert self.stack is not None, "Stack must be provided"
		assert isinstance(self.stack, models.Model), "Stack must be a valid Stack instance"
		self.name = f"{RESOURCE_NAME}_{self.index}"
		super().save(*args, **kwargs)
