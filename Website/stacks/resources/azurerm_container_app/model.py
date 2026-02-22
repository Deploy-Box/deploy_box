import os
from django.db import models

from core.fields import ShortUUIDField
from stacks.resources.base_resource_model import BaseResourceModel

CLASS_PREFIX = "res007"
RESOURCE_NAME = "azurerm_container_app"

class AzurermContainerApp(BaseResourceModel):
	id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)
	azurerm_id = models.CharField(max_length=255)
	azurerm_name = models.CharField(max_length=255)
	container_app_environment_id = models.CharField(max_length=255)
	resource_group_name = models.CharField(max_length=255)
	revision_mode = models.CharField(max_length=50, default='Single')
	tags = models.JSONField(default=dict, blank=True)
	workload_profile_name = models.CharField(max_length=255, blank=True, default='')
	ingress_allow_insecure_connections = models.BooleanField(default=False)
	ingress_client_certificate_mode = models.CharField(max_length=50, default='ignore')
	ingress_exposed_port = models.IntegerField(default=80)
	ingress_external_enabled = models.BooleanField(default=True)
	ingress_target_port = models.IntegerField(default=80)
	ingress_transport = models.CharField(max_length=50, default='auto')
	ingress_traffic_weight_label = models.CharField(max_length=255, blank=True, default='')
	ingress_traffic_weight_latest_revision = models.BooleanField(default=True)
	ingress_traffic_weight_percentage = models.IntegerField(default=100)
	ingress_traffic_weight_revision_suffix = models.CharField(max_length=100, blank=True, default='')
	template_max_replicas = models.IntegerField(default=1)
	template_min_replicas = models.IntegerField(default=0)
	template_revision_suffix = models.CharField(max_length=100, blank=True, default='')
	template_termination_grace_period_seconds = models.IntegerField(default=30)
	template_container_args = models.JSONField(default=list, blank=True)
	template_container_command = models.JSONField(default=list, blank=True)
	template_container_name = models.CharField(max_length=255, blank=True, default='')
	template_container_image = models.CharField(max_length=255, blank=True, default='')
	template_container_cpu = models.CharField(max_length=50, default='0.25')
	template_container_memory = models.CharField(max_length=50, default='0.5Gi')
	template_container_env = models.JSONField(default=list, blank=True)
	template_container_build_context = models.CharField(max_length=255, blank=True, default='')
	configuration_active_revision_mode = models.CharField(max_length=50, default='Single')
	configuration_ingress_external = models.BooleanField(default=True)
	configuration_ingress_target_port = models.IntegerField(default=80)

	def __str__(self):
		return self.azurerm_name
	
	def save(self, *args, **kwargs):
		assert self.stack is not None, "Stack must be provided"
		assert isinstance(self.stack, models.Model), "Stack must be a valid Stack instance"
		environment = os.getenv('ENV', 'DEV').lower()
		self.name = f"{RESOURCE_NAME}_{self.index}"
		if environment == 'prod':
			self.azurerm_name = f"{CLASS_PREFIX}-{self.index}-{self.stack.pk}"
		else:
			self.azurerm_name = f"{CLASS_PREFIX}-{self.index}-{self.stack.pk}-{environment}"

		if not self.template_container_name:
			self.template_container_name = f'container-{self.stack.pk}'
		
		super().save(*args, **kwargs)

