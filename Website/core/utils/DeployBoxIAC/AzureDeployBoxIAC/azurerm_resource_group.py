from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from azure_deploy_box_iac import AzureDeployBoxIAC

RESOURCE_NAME = "azurerm_resource_group"

class AzureResourceGroup:
    """Azure Resource Group IAC class"""
    azurerm_resource_group_id = "1234"

    def __init__(self, parent: AzureDeployBoxIAC) -> None:
        self.parent = parent

    def plan(self, stack_id: str, iac: dict) -> dict:
        rg_name = f"{stack_id}-rg"
        rg_location = iac.get(RESOURCE_NAME, {}).get("rg", {}).get("location")
        rg_tags = iac.get(RESOURCE_NAME, {}).get("rg", {}).get("tags", {})

        rg = {
            "name": rg_name,
            "location": rg_location if rg_location else "eastus",
            "tags": rg_tags,
        }

        return {
            RESOURCE_NAME: {
                "rg": rg
            }
        }
    
    @staticmethod
    def deploy(stack_id: str, iac: dict) -> bool:
        return True
