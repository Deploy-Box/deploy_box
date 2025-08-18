from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from azure_deploy_box_iac import AzureDeployBoxIAC

RESOURCE_NAME = "azurerm_container_app_environment"

class AzureContainerAppEnvironment:
    """Azure Container App Environment IAC class"""
    azurerm_container_app_environment_id = "1234"

    def __init__(self, parent: AzureDeployBoxIAC) -> None:
        self.parent = parent

    def plan(self, stack_id: str, iac: dict) -> dict:
        resource = iac.get(RESOURCE_NAME)

        if not resource:
            print(f"No {RESOURCE_NAME} found in IAC for stack {stack_id}")
            return {}

        ca_environment_id = f"{stack_id}-ca-env"
        ca_name = f"container-app-{stack_id}"
        ca_resource_group = self.parent.azurerm_resource_group.azurerm_resource_group_id
        ca_revision_mode = iac.get("azurerm_container_app", {}).get(ca_name, {}).get("revision_mode", "Single")
        ca_template = {}


        ca = {
            "container_app_environment_id": f"${{azurerm_container_app_environment.{ca_environment_id}.id}}",
            "name": ca_name,
            "resource_group_name": f"{stack_id}-rg",
            "revision_mode": ca_revision_mode,
            "template": ca_template,
            "dapr": None,
            "identity": {
                "type": "SystemAssigned",
            },
            "ingress": {
                "external": True,
                "target_port": 80,
                "transport": "http",
            },
            "registry": [],
            "secret": [],
            "workload_profile_name": "default",
            "tags": {
            }

        }

        return {
            RESOURCE_NAME: {
                "ca": ca
            }
        }
    
    @staticmethod
    def deploy(stack_id: str, iac: dict) -> bool:
        return True
