from __future__ import annotations

from django.db import models
from typing import TYPE_CHECKING, Any

from .resource_manager import ResourceManager

from stacks.resources.azurerm_resource_group.manager import AzurermResourceGroupManager
from stacks.resources.azurerm_container_app.manager import AzurermContainerAppManager
from stacks.resources.azurerm_storage_account.manager import AzurermStorageAccountManager
from stacks.resources.azurerm_storage_container.manager import AzurermStorageContainerManager
from stacks.resources.azurerm_container_app_environment.manager import AzurermContainerAppEnvironmentManager
from stacks.resources.deployboxrm_workos_integration.manager import DeployBoxrmWorkOSIntegrationManager
from stacks.resources.thenilerm_database.manager import TheNilermDatabaseManager
from stacks.resources.azurerm_storage_account_static_website.manager import AzurermStorageAccountStaticWebsiteManager

if TYPE_CHECKING:
    from stacks.models import Stack

RESOURCE_MANAGER_MAPPING: dict[str, type[ResourceManager]] = {
        "AZURERM_RESOURCE_GROUP": AzurermResourceGroupManager,
        "AZURERM_CONTAINER_APP": AzurermContainerAppManager,
        "AZURERM_STORAGE_ACCOUNT": AzurermStorageAccountManager,
        "AZURERM_STORAGE_CONTAINER": AzurermStorageContainerManager,
        "AZURERM_CONTAINER_APP_ENVIRONMENT": AzurermContainerAppEnvironmentManager,
        "THENILERM_DATABASE": TheNilermDatabaseManager,
        "DEPLOYBOXRM_WORKOS_INTEGRATION": DeployBoxrmWorkOSIntegrationManager,
        "AZURERM_STORAGE_ACCOUNT_STATIC_WEBSITE": AzurermStorageAccountStaticWebsiteManager,
    }

class ResourcesManager():
    resource_prefix_mapping = None

    @staticmethod
    def get_resource_prefix_mapping() -> dict[str, type[ResourceManager]]:
        if ResourcesManager.resource_prefix_mapping is None:
            ResourcesManager.resource_prefix_mapping = {
                manager_class.get_resource_prefix(): manager_class
                for manager_class in RESOURCE_MANAGER_MAPPING.values()
            }

            if len(ResourcesManager.resource_prefix_mapping) != len(RESOURCE_MANAGER_MAPPING):
                raise ValueError("Duplicate resource prefixes found in resource managers.")
            
        return ResourcesManager.resource_prefix_mapping

    @staticmethod
    def create(resources: dict, stack: Stack) -> list[models.Model]:
        created_resources = []
        
        for resource in resources:
            assert isinstance(resource, dict), f"Expected resource to be a dict, got {type(resource)}"

            resource.update({"stack": stack})
            resource_type = resource["resource_type"]

            assert isinstance(resource_type, str), f"Expected resource_type to be a str, got {type(resource_type)}"

            if resource_type.upper() in RESOURCE_MANAGER_MAPPING:
                model = RESOURCE_MANAGER_MAPPING[resource_type.upper()].get_model()
                created_resource = model.objects.create(**create_filtered_data(resource, model))
                created_resources.append(created_resource)
            else:
                raise ValueError(f"Unknown resource type: {resource_type}")
        return created_resources
    
    @staticmethod
    def read(resource_id: str | list[str]) -> models.Model | list[models.Model] | None:
        if isinstance(resource_id, list):
            return [ResourcesManager.read(rid) for rid in resource_id]
        
        resource_prefix_mapping = ResourcesManager.get_resource_prefix_mapping()
        prefix = resource_id.split('_')[0]
        
        if prefix in resource_prefix_mapping:
            manager_class = resource_prefix_mapping[prefix]
            managed_model_class = manager_class.get_model()
            try:
                return managed_model_class.objects.get(pk=resource_id)
            except Exception as e:
                print(f"Error retrieving resource {resource_id}: {e}")
                
        return None
    
    @staticmethod
    def serialize(resource: models.Model | list[models.Model]):
        if isinstance(resource, list):
            return [ResourcesManager.serialize(r) for r in resource]
        
        resource_prefix_mapping = ResourcesManager.get_resource_prefix_mapping()
        prefix = resource.pk.split('_')[0]
        if prefix in resource_prefix_mapping:
            manager_class = resource_prefix_mapping[prefix]
            return manager_class().serialize(resource)
        print(f"Unknown resource prefix: {prefix}")
        return None
    
def create_filtered_data(data: dict, model: type[models.Model]) -> dict[str, Any]:
    # Get writable field names from the model (excludes auto fields, reverse relations)
    model_fields = {
        f.name for f in model._meta.get_fields()
        if not f.auto_created and not f.many_to_many and not f.one_to_many
    }
    return {k: v for k, v in data.items() if k in model_fields}