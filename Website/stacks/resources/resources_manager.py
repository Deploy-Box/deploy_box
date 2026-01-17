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

if TYPE_CHECKING:
    from stacks.models import Stack


def get_resource_manager_mapping() -> dict[str, type[ResourceManager]]:
    return {
        "AZURERM_RESOURCE_GROUP": AzurermResourceGroupManager,
        "AZURERM_CONTAINER_APP": AzurermContainerAppManager,
        "AZURERM_STORAGE_ACCOUNT": AzurermStorageAccountManager,
        "AZURERM_STORAGE_CONTAINER": AzurermStorageContainerManager,
        "AZURERM_CONTAINER_APP_ENVIRONMENT": AzurermContainerAppEnvironmentManager,
        "THENILERM_DATABASE": TheNilermDatabaseManager,
        "DEPLOYBOXRM_WORKOS_INTEGRATION": DeployBoxrmWorkOSIntegrationManager,
    }

def get_resource_model_mapping() -> dict[str, type[models.Model]]:
    from stacks.resources.azurerm_resource_group.model import AzurermResourceGroup
    from stacks.resources.azurerm_container_app.model import AzurermContainerApp
    from stacks.resources.azurerm_storage_account.model import AzurermStorageAccount
    from stacks.resources.azurerm_storage_container.model import AzurermStorageContainer
    from stacks.resources.azurerm_container_app_environment.model import AzurermContainerAppEnvironment
    from stacks.resources.deployboxrm_workos_integration.model import DeployBoxrmWorkOSIntegration

    return {
        "AZURERM_RESOURCE_GROUP": AzurermResourceGroup,
        "AZURERM_CONTAINER_APP": AzurermContainerApp,
        "AZURERM_STORAGE_ACCOUNT": AzurermStorageAccount,
        "AZURERM_STORAGE_CONTAINER": AzurermStorageContainer,
        "AZURERM_CONTAINER_APP_ENVIRONMENT": AzurermContainerAppEnvironment,
        "DEPLOYBOXRM_WORKOS_INTEGRATION": DeployBoxrmWorkOSIntegration,
        "THENILERM_DATABASE": TheNilermDatabaseManager.get_model(),
    }

class ResourcesManager():
    resource_manager_mapping = None
    resource_model_mapping = None
    resource_prefix_mapping = None

    @staticmethod
    def get_resource_manager_mapping() -> dict[str, type[ResourceManager]]:
        if ResourcesManager.resource_manager_mapping is None:
            ResourcesManager.resource_manager_mapping = get_resource_manager_mapping()
        return ResourcesManager.resource_manager_mapping
    
    @staticmethod
    def get_resource_model_mapping() -> dict[str, type[models.Model]]:
        if ResourcesManager.resource_model_mapping is None:
            ResourcesManager.resource_model_mapping = get_resource_model_mapping()
        return ResourcesManager.resource_model_mapping
    
    @staticmethod
    def get_resource_prefix_mapping() -> dict[str, type[ResourceManager]]:
        if ResourcesManager.resource_prefix_mapping is None:
            ResourcesManager.resource_prefix_mapping = {
                manager_class.get_resource_prefix(): manager_class
                for manager_class in ResourcesManager.get_resource_manager_mapping().values()
            }

            if len(ResourcesManager.resource_prefix_mapping) != len(ResourcesManager.get_resource_manager_mapping()):
                raise ValueError("Duplicate resource prefixes found in resource managers.")
            
        return ResourcesManager.resource_prefix_mapping

    @staticmethod
    def create(resources: dict, stack: Stack) -> list[models.Model]:
        resource_model_mapping = ResourcesManager.get_resource_manager_mapping()
        created_resources = []
        
        for resource in resources:
            assert isinstance(resource, dict), f"Expected resource to be a dict, got {type(resource)}"

            resource.update({"stack": stack})
            resource_type = resource["resource_type"]

            assert isinstance(resource_type, str), f"Expected resource_type to be a str, got {type(resource_type)}"

            if resource_type.upper() in resource_model_mapping:
                model = resource_model_mapping[resource_type.upper()]().get_model()
                created_resource = model.objects.create(**create_filtered_data(resource, model))
                created_resources.append(created_resource)
            else:
                raise ValueError(f"Unknown resource type: {resource_type}")
        return created_resources
    
    @staticmethod
    def read(resource_id: str | list[str]):
        if isinstance(resource_id, list):
            return [ResourcesManager.read(rid) for rid in resource_id]
        
        resource_prefix_mapping = ResourcesManager.get_resource_prefix_mapping()
        # Extract prefix from resource_id (assuming format: "prefix-identifier")
        prefix = resource_id.split('-')[0]
        
        if prefix in resource_prefix_mapping:
            manager_class = resource_prefix_mapping[prefix]
            try:
                return
                # return manager_class().objects.get(pk=resource_id)
            except models.Model.DoesNotExist:
                pass
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