from __future__ import annotations

from django.db import models
from typing import TYPE_CHECKING, Any, overload

from .resource_manager import ResourceManager

from stacks.models import Stack
from stacks.resources.azurerm_resource_group.manager import AzurermResourceGroupManager
from stacks.resources.azurerm_container_app.manager import AzurermContainerAppManager
from stacks.resources.azurerm_storage_account.manager import AzurermStorageAccountManager
from stacks.resources.azurerm_storage_container.manager import AzurermStorageContainerManager
from stacks.resources.azurerm_container_app_environment.manager import AzurermContainerAppEnvironmentManager
from stacks.resources.deployboxrm_workos_integration.manager import DeployBoxrmWorkOSIntegrationManager
from stacks.resources.thenilerm_database.manager import TheNilermDatabaseManager
from stacks.resources.azurerm_storage_account_static_website.manager import AzurermStorageAccountStaticWebsiteManager
from stacks.resources.deployboxrm_edge.manager import DeployBoxrmEdgeManager
from stacks.resources.azurerm_log_analytics_workspace.manager import AzurermLogAnalyticsWorkspaceManager
from stacks.resources.azurerm_key_vault.manager import AzurermKeyVaultManager
from stacks.resources.deployboxrm_postgres_database.manager import DeployBoxrmPostgresDatabaseManager
from stacks.resources.azurerm_public_ip.manager import AzurermPublicIpManager
from stacks.resources.azurerm_network_security_group.manager import AzurermNetworkSecurityGroupManager
from stacks.resources.azurerm_virtual_network.manager import AzurermVirtualNetworkManager
from stacks.resources.azurerm_network_interface.manager import AzurermNetworkInterfaceManager
from stacks.resources.azurerm_linux_virtual_machine.manager import AzurermLinuxVirtualMachineManager

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
        "DEPLOYBOXRM_EDGE": DeployBoxrmEdgeManager,
        "AZURERM_LOG_ANALYTICS_WORKSPACE": AzurermLogAnalyticsWorkspaceManager,
        "AZURERM_KEY_VAULT": AzurermKeyVaultManager,
        "DEPLOYBOXRM_POSTGRES_DATABASE": DeployBoxrmPostgresDatabaseManager,
        "AZURERM_PUBLIC_IP": AzurermPublicIpManager,
        "AZURERM_NETWORK_SECURITY_GROUP": AzurermNetworkSecurityGroupManager,
        "AZURERM_VIRTUAL_NETWORK": AzurermVirtualNetworkManager,
        "AZURERM_NETWORK_INTERFACE": AzurermNetworkInterfaceManager,
        "AZURERM_LINUX_VIRTUAL_MACHINE": AzurermLinuxVirtualMachineManager,
    }

RESOURCE_TYPE_DISPLAY_NAMES: dict[str, str] = {
    "AZURERM_RESOURCE_GROUP": "Resource Group",
    "AZURERM_CONTAINER_APP": "Container App",
    "AZURERM_STORAGE_ACCOUNT": "Storage Account",
    "AZURERM_STORAGE_CONTAINER": "Storage Container",
    "AZURERM_CONTAINER_APP_ENVIRONMENT": "Container App Environment",
    "THENILERM_DATABASE": "Nile Database",
    "DEPLOYBOXRM_WORKOS_INTEGRATION": "WorkOS Integration",
    "AZURERM_STORAGE_ACCOUNT_STATIC_WEBSITE": "Static Website",
    "DEPLOYBOXRM_EDGE": "Edge Router",
    "AZURERM_LOG_ANALYTICS_WORKSPACE": "Log Analytics Workspace",
    "AZURERM_KEY_VAULT": "Key Vault",
    "DEPLOYBOXRM_POSTGRES_DATABASE": "Postgres Database",
    "AZURERM_PUBLIC_IP": "Public IP",
    "AZURERM_NETWORK_SECURITY_GROUP": "Network Security Group",
    "AZURERM_VIRTUAL_NETWORK": "Virtual Network",
    "AZURERM_NETWORK_INTERFACE": "Network Interface",
    "AZURERM_LINUX_VIRTUAL_MACHINE": "Linux Virtual Machine",
}

RESOURCE_TYPE_CATEGORIES: dict[str, str] = {
    "AZURERM_RESOURCE_GROUP": "Infrastructure",
    "AZURERM_CONTAINER_APP": "Compute",
    "AZURERM_CONTAINER_APP_ENVIRONMENT": "Compute",
    "AZURERM_LINUX_VIRTUAL_MACHINE": "Compute",
    "AZURERM_STORAGE_ACCOUNT": "Storage",
    "AZURERM_STORAGE_CONTAINER": "Storage",
    "AZURERM_STORAGE_ACCOUNT_STATIC_WEBSITE": "Storage",
    "AZURERM_KEY_VAULT": "Security",
    "AZURERM_NETWORK_SECURITY_GROUP": "Networking",
    "AZURERM_VIRTUAL_NETWORK": "Networking",
    "AZURERM_NETWORK_INTERFACE": "Networking",
    "AZURERM_PUBLIC_IP": "Networking",
    "AZURERM_LOG_ANALYTICS_WORKSPACE": "Monitoring",
    "THENILERM_DATABASE": "Database",
    "DEPLOYBOXRM_POSTGRES_DATABASE": "Database",
    "DEPLOYBOXRM_WORKOS_INTEGRATION": "Authentication",
    "DEPLOYBOXRM_EDGE": "Networking",
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
    def add_resource(stack: Stack, resource_type: str, config: dict | None = None) -> models.Model:
        """Add a single resource to an existing stack.

        Returns the newly created resource instance.
        Raises ``ValueError`` if *resource_type* is unknown.
        """
        key = resource_type.upper()
        if key not in RESOURCE_MANAGER_MAPPING:
            raise ValueError(f"Unknown resource type: {resource_type}")

        existing = ResourcesManager.get_from_stack(stack)
        same_type = [r for r in existing if type(r) == RESOURCE_MANAGER_MAPPING[key].get_model()]
        next_index = max((r.index for r in same_type), default=-1) + 1

        data: dict[str, Any] = {
            "stack": stack,
            "resource_type": key,
            "name": f"{RESOURCE_TYPE_DISPLAY_NAMES.get(key, key)} {next_index + 1}",
            "index": next_index,
            **(config or {}),
        }

        model = RESOURCE_MANAGER_MAPPING[key].get_model()
        return model.objects.create(**create_filtered_data(data, model))

    @staticmethod
    def remove_resource(resource_id: str) -> bool:
        """Delete a single resource by its prefixed ID.

        Returns ``True`` if the resource was deleted, ``False`` if not found.
        """
        resource = ResourcesManager._read_one(resource_id)
        if resource is None:
            return False
        resource.delete()
        return True

    @staticmethod
    def get_available_resource_types() -> list[dict[str, str]]:
        """Return a catalogue of resource types that can be added to a stack."""
        return [
            {
                "resource_type": key,
                "display_name": RESOURCE_TYPE_DISPLAY_NAMES.get(key, key),
                "category": RESOURCE_TYPE_CATEGORIES.get(key, "Other"),
            }
            for key in RESOURCE_MANAGER_MAPPING
        ]

    @staticmethod
    def get_from_stack(stack: Stack) -> list[models.Model]:
        resources = []
        for resource_manager in RESOURCE_MANAGER_MAPPING.values():
            managed_model_class = resource_manager.get_model()
            resources.extend(managed_model_class.objects.filter(stack=stack))
        return resources
    
    @staticmethod
    def _read_one(resource_id: str) -> models.Model | None:
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

    @overload
    @staticmethod
    def read(resource_id: str) -> models.Model | None: ...
    
    @overload
    @staticmethod
    def read(resource_id: list[str]) -> list[models.Model | None]: ...

    @staticmethod
    def read(resource_id: str | list[str]) -> models.Model | list[models.Model | None] | None:
        if isinstance(resource_id, list):
            return [ResourcesManager._read_one(rid) for rid in resource_id]
        
        return ResourcesManager._read_one(resource_id)
    
    @staticmethod
    def delete(stack: Stack):
        for resource_manager in RESOURCE_MANAGER_MAPPING.values():
            managed_model_class = resource_manager.get_model()
            managed_model_class.objects.filter(stack=stack).delete()

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