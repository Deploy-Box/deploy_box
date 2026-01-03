import uuid
from django.db import models, transaction

from stacks.resources import (
    AzurermResourceGroup,
    AzurermStorageAccount,
    AzurermDnsCnameRecord
)
from core.fields import ShortUUIDField

CLASS_PREFIX = "itm_001"

class DeployBoxStaticWebsiteItem(models.Model):
    id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)
    name = models.CharField(max_length=255, blank=False, null=False)
    stack = models.ForeignKey('stacks.Stack', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Resources
    azurerm_resource_group = models.ForeignKey('stacks.AzurermResourceGroup', on_delete=models.CASCADE)
    azurerm_storage_account = models.ForeignKey('stacks.AzurermStorageAccount', on_delete=models.CASCADE)
    azurerm_dns_cname_record = models.ForeignKey('stacks.AzurermDnsCnameRecord', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        assert self.stack is not None, "Stack must be provided in data"
        assert isinstance(self.stack, models.Model), "Stack must be a valid Stack instance"

        name_uuid = str(uuid.uuid4())[:8]

        with transaction.atomic():
            self.azurerm_resource_group = AzurermResourceGroup.objects.create(
                stack=self.stack,
                name='azurerm_resource_group_' + name_uuid
            )
            self.azurerm_storage_account = AzurermStorageAccount.objects.create(
                stack=self.stack,
                name='azurerm_storage_account_' + name_uuid,
                resource_group_name=f"${{azurerm_resource_group.{self.azurerm_resource_group.name}.name}}",
                https_traffic_only_enabled=False,
                public_network_access_enabled=True,
                allow_nested_items_to_be_public=True,
                static_website_index_document="index.html",
                static_website_error_404_document="not_found.html",
                custom_domain_name=f"{self.stack.pk}.dev.deploy-box.com",
                custom_domain_use_subdomain=False
            )
            self.azurerm_dns_cname_record = AzurermDnsCnameRecord.objects.create(
                stack=self.stack,
                name='azurerm_dns_cname_record_' + name_uuid,
                azurerm_name=self.stack.pk,
                resource_group_name="deploy-box-rg-dev",
                zone_name="dev.deploy-box.com",
                ttl=3600,
                record=f"${{azurerm_storage_account.{self.azurerm_storage_account.name}.primary_web_host}}"
            )
            
        
            super().save(*args, **kwargs)