from __future__ import annotations
from pydantic import BaseModel, Field
from typing import TYPE_CHECKING, List
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from azure_deploy_box_iac import AzureDeployBoxIAC

RESOURCE_NAME = "azurerm_container_app"

class Container(BaseModel):
    name: str = "1"
    cpu: float = 0.25
    memory: str = "0.5Gi"
    env: list = []
    image: str

    @classmethod
    def __dict__(cls, **data):
        if "name" not in data:
            data["name"] = f"container-app-{data.get('index', 0)}"
        return super().__dict__(**data)

class Template(BaseModel):
    container: List[Container]
    max_replicas: int = 10
    min_replicas: int = 0

@dataclass
class ContainerAppDefaults:
    name: str = "container-app-{index}"
    revision_mode: str = "Single"
    max_replicas: int = 10
    min_replicas: int = 0
    ingress_external: bool = True
    ingress_target_port: int = 80
    ingress_transport: str = "http"
    ingress_traffic_weight: list = field(default_factory=lambda: [{"latest_revision": True, "percentage": 100}])

class AzureContainerApp:
    """Azure Container App IAC class"""

    def __init__(self, parent: AzureDeployBoxIAC) -> None:
        self.parent = parent
        self.defaults = ContainerAppDefaults()

    def plan(self, stack_id: str, iac: dict) -> None:
        resources = iac.get(RESOURCE_NAME, {})
        if not resources:
            logger.warning(f"No {RESOURCE_NAME} found in IAC for stack {stack_id}")
            return

        ensure_dict(resources, f"Resources for {RESOURCE_NAME}")
        
        for index, (resource_name, resource) in enumerate(resources.items()):
            ensure_dict(resource, f"Resource {resource_name}")
            
            # Container App Core Config
            ca_name = resource.get("name", self._under_to_dash(self.defaults.name.format(index=index)))
            ca_revision_mode = resource.get("revision_mode", self.defaults.revision_mode)

            # Template
            template_dict = ensure_dict(resource.get("template", {}), f"Template for {resource_name}")
            template = Template(**template_dict)
            print(template.container)
            
            # container_list = self._process_containers(ensure_list(template_dict.get("container", []), "container"), resource_name)
            # template = {
            #     "container": container_list,
            #     "max_replicas": template_dict.get("max_replicas", self.defaults.max_replicas),
            #     "min_replicas": template_dict.get("min_replicas", self.defaults.min_replicas),
            # }

            # Ingress
            ingress_dict = ensure_dict(resource.get("ingress", {}), f"Ingress for {resource_name}")
            ingress = {
                "external": ingress_dict.get("external", self.defaults.ingress_external),
                "target_port": ingress_dict.get("target_port", self.defaults.ingress_target_port),
                "transport": ingress_dict.get("transport", self.defaults.ingress_transport),
                "traffic_weight": ingress_dict.get("traffic_weight", self.defaults.ingress_traffic_weight),
            }

            # Secrets
            secret = self._merge_secrets(
                [{"name": "acr-password", "value": self.parent.registry_password}],
                resource.get("secret", [])
            )

            # Registry
            registry = [{
                "server": f"{self.parent.registry_name}.azurecr.io",
                "username": self.parent.registry_name,
                "password_secret_name": "acr-password"
            }]

            # Final Assembly
            ca = {
                "container_app_environment_id": self.parent.azurerm_container_app_environment.azurerm_container_app_environment_id,
                "name": ca_name,
                "resource_group_name": self.parent.azurerm_resource_group.azurerm_resource_group_id,
                "revision_mode": ca_revision_mode,
                "template": template,
                "ingress": ingress,
                "registry": registry,
                "secret": secret,
                "tags": {}
            }

            resources[resource_name] = ca
    
    def _merge_secrets(self, existing_secrets: list, new_secrets: list) -> list:
        """Merge existing secrets with new secrets, avoiding duplicates"""
        secret_names = {secret['name'] for secret in existing_secrets}
        merged_secrets = existing_secrets.copy()

        for new_secret in new_secrets:
            if new_secret['name'] not in secret_names:
                merged_secrets.append(new_secret)
                secret_names.add(new_secret['name'])

        return merged_secrets

    def _under_to_dash(self, name: str) -> str:
        """Convert a name from under_score to dash-format"""
        return name.replace("_", "-")
    
    def _process_containers(self, containers: list, resource_name: str) -> list:
        processed = []
        for index, container in enumerate(containers):
            ensure_dict(container, f"Container #{index} in {resource_name}")
            container = {k: v for k, v in container.items() if k in {"name", "cpu", "memory", "env", "image"}}
            container.setdefault("name", self._under_to_dash(f"{resource_name}-container-{index}"))
            container.setdefault("cpu", 0.25)
            container.setdefault("memory", "0.5Gi")
            container.setdefault("env", [])
            
            image = container.get("image")
            if not image:
                raise ValueError(f"Image must be specified for container in {resource_name}")
            
            container["image"] = f"{self.parent.registry_name}.azurecr.io/{image}"
            processed.append(container)
        return processed

def ensure_dict(obj: object, name: str) -> dict:
    if not isinstance(obj, dict):
        raise ValueError(f"{name} must be a dictionary")
    return obj

def ensure_list(obj: object, name: str) -> list:
    if not isinstance(obj, list):
        raise ValueError(f"{name} must be a list")
    return obj
