from __future__ import annotations

from django.db import models
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from stacks.models import Stack


class ResourceMeta(ABCMeta, type(models.Model)):
    pass


class Resource(models.Model, metaclass=ResourceMeta):
    class Meta:
        abstract = True
    
    @staticmethod
    @abstractmethod
    def get_resource_prefix() -> str:
        pass
    
    def serialize(self, resource: models.Model) -> dict:
        return {}

def get_resource_manager_mapping() -> dict[str, type[Resource]]:
    """Lazy import to avoid circular dependencies"""
    from stacks.resources.azurerm_container_app.manager import AzurermContainerAppManager
    from stacks.resources.azurerm_storage_account.manager import AzurermStorageAccountManager
    from stacks.resources.azurerm_storage_container.manager import AzurermStorageContainerManager

    return {
        "AZURERM_CONTAINER_APP": AzurermContainerAppManager,
        "AZURERM_STORAGE_ACCOUNT": AzurermStorageAccountManager,
        "AZURERM_STORAGE_CONTAINER": AzurermStorageContainerManager,
    }

class ResourceManager():
    resource_manager_mapping = None
    resource_prefix_mapping = None

    @staticmethod
    def get_resource_manager_mapping() -> dict[str, type[Resource]]:
        if ResourceManager.resource_manager_mapping is None:
            ResourceManager.resource_manager_mapping = get_resource_manager_mapping()
        return ResourceManager.resource_manager_mapping
    
    @staticmethod
    def get_resource_prefix_mapping() -> dict[str, type[Resource]]:
        if ResourceManager.resource_prefix_mapping is None:
            ResourceManager.resource_prefix_mapping = {
                manager_class.get_resource_prefix(): manager_class
                for manager_class in ResourceManager.get_resource_manager_mapping().values()
            }

            if len(ResourceManager.resource_prefix_mapping) != len(ResourceManager.get_resource_manager_mapping()):
                raise ValueError("Duplicate resource prefixes found in resource managers.")
            
        return ResourceManager.resource_prefix_mapping

    @staticmethod
    def create(resources: dict, stack: Stack) -> list[models.Model]:
        resource_manager_mapping = ResourceManager.get_resource_manager_mapping()
        created_resources = []
        
        for resource in resources:
            assert isinstance(resource, dict), f"Expected resource to be a dict, got {type(resource)}"

            resource.update({"stack": stack})
            resource_type = resource["resource_type"]

            assert isinstance(resource_type, str), f"Expected resource_type to be a str, got {type(resource_type)}"

            if resource_type.upper() in resource_manager_mapping:
                created_resource = resource_manager_mapping[resource_type.upper()]().objects.create(**resource)
                created_resources.append(created_resource)
        return created_resources
    
    @staticmethod
    def read(resource_id: str | list[str]):
        if isinstance(resource_id, list):
            return [ResourceManager.read(rid) for rid in resource_id]
        
        resource_prefix_mapping = ResourceManager.get_resource_prefix_mapping()
        # Extract prefix from resource_id (assuming format: "prefix-identifier")
        prefix = resource_id.split('-')[0]
        
        if prefix in resource_prefix_mapping:
            manager_class = resource_prefix_mapping[prefix]
            try:
                return manager_class().objects.get(pk=resource_id)
            except models.Model.DoesNotExist:
                pass
        return None
    
    @staticmethod
    def serialize(resource: models.Model | list[models.Model]):
        if isinstance(resource, list):
            return [ResourceManager.serialize(r) for r in resource]
        resource_prefix_mapping = ResourceManager.get_resource_prefix_mapping()
        prefix = resource.pk.split('_')[0]
        if prefix in resource_prefix_mapping:
            manager_class = resource_prefix_mapping[prefix]
            return manager_class().serialize(resource)
        return None
    
def create_filtered_data(data: dict, model: type[models.Model]) -> dict[str, Any]:
        # Get writable field names from the model (excludes auto fields, reverse relations)
        model_fields = {
            f.name for f in model._meta.get_fields()
            if not f.auto_created and not f.many_to_many and not f.one_to_many
        }
        return {k: v for k, v in data.items() if k in model_fields}