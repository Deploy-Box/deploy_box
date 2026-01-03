from django.db import models, transaction

from stacks.resources import (
    AzurermResourceGroup, AzurermResourceGroupSerializer,
    AzurermStorageAccount, AzurermStorageAccountSerializer,
    AzurermDnsCnameRecord, AzurermDnsCnameRecordSerializer
)
from .model import DeployBoxStaticWebsiteItem, CLASS_PREFIX

class DeployBoxStaticWebsiteItemManager():
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    def serialize(self, resource: DeployBoxStaticWebsiteItem) -> list[dict]:
        return [
            dict(AzurermResourceGroupSerializer(resource.azurerm_resource_group).data),
            dict(AzurermStorageAccountSerializer(resource.azurerm_storage_account).data),
            dict(AzurermDnsCnameRecordSerializer(resource.azurerm_dns_cname_record).data),
        ]

    
    
