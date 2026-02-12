from django.db import models
from django.conf import settings

from core.fields import ShortUUIDField
from stacks.resources.base_resource_model import BaseResourceModel

CLASS_PREFIX = "res00B"
RESOURCE_NAME = "deployboxrm_edge"

class DeployBoxrmEdge(BaseResourceModel):
	id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)

	# Resource specific fields
	subdomain = models.CharField(max_length=255)
	root_base_url = models.CharField(max_length=255)
	resolved_root_base_url = models.CharField(max_length=255, default=f'{settings.HOST}/still-configuring/')
	api_base_url = models.CharField(max_length=255, blank=True, null=True)
	resolved_api_base_url = models.CharField(max_length=255, blank=True, null=True)

	class Meta(BaseResourceModel.Meta):
		constraints = [
			models.UniqueConstraint(
				fields=["subdomain"],
				name="uniq_deployboxrm_edge_subdomain",
			),
		]

	def __str__(self):
		return f"{RESOURCE_NAME}.{self.name}"
    
	def save(self, *args, **kwargs):
		assert self.stack is not None, "Stack must be provided"
		assert isinstance(self.stack, models.Model), "Stack must be a valid Stack instance"
		self.name = f"{RESOURCE_NAME}_{self.index}"

		if not self.subdomain:
			self.subdomain = f"{self.stack.pk}{self.index}"

		if not self.resolved_root_base_url:
			self.resolved_root_base_url = f"{settings.HOST}/still-configuring/"

		super().save(*args, **kwargs)
