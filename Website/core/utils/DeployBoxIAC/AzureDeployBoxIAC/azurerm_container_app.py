from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from typing import TYPE_CHECKING, List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from azure_deploy_box_iac import AzureDeployBoxIAC

RESOURCE_NAME = "azurerm_container_app"

class EnvironmentVariable(BaseModel):
    name: str
    value: Optional[str] = None
    secret_name: Optional[str] = None

class Container(BaseModel):
    name: str = "1"
    cpu: float = 0.25
    memory: str = "0.5Gi"
    image: str
    env: List[EnvironmentVariable] = Field(default_factory=list)

class Template(BaseModel):
    container: List[Container]
    max_replicas: int = 10
    min_replicas: int = 0

    @model_validator(mode="before")
    def check_containers_exist(cls, values):
        containers = values.get('container', [])
        if not containers:
            raise ValueError("At least one container must be defined in a template.")
        return values

class TrafficWeight(BaseModel):
    latest_revision: bool = True
    percentage: int = 100

class Ingress(BaseModel):
    external: bool = True
    target_port: int = 80
    transport: str = "http"
    traffic_weight: List[TrafficWeight] = Field(default_factory=lambda: [TrafficWeight()])

class Secret(BaseModel):
    name: str
    value: str

class Registry(BaseModel):
    server: str
    username: str
    password_secret_name: str

class ContainerApp(BaseModel):
    container_app_environment_id: str
    name: str
    resource_group_name: str
    revision_mode: str = "Single"
    template: Template
    ingress: Ingress
    registry: List[Registry]
    secret: List[Secret]
    tags: Dict[str, Any] = Field(default_factory=dict)

class AzureContainerApp:
    """Azure Container App IAC class"""

    def __init__(self, parent: AzureDeployBoxIAC) -> None:
        self.parent = parent
        self.container_app_list: List[ContainerApp] = []

    def plan(self, stack_id: str, iac: dict) -> None:
        resources = iac.get(RESOURCE_NAME, {})
        if not resources:
            logger.warning(f"No {RESOURCE_NAME} found in IAC for stack {stack_id}")
            return

        ensure_dict(resources, f"Resources for {RESOURCE_NAME}")
        
        for index, (resource_name, resource) in enumerate(resources.items()):
            ensure_dict(resource, f"Resource {resource_name}")
            
            # Container App Core Config
            ca_name = resource.get("name", self._under_to_dash(f"container-app-{index}"))

            # Template - let Pydantic handle defaults
            template_dict = ensure_dict(resource.get("template", {}), f"Template for {resource_name}")
            template = Template(**template_dict)
            
            # Ingress - let Pydantic handle defaults
            ingress_dict = ensure_dict(resource.get("ingress", {}), f"Ingress for {resource_name}")
            ingress = Ingress(**ingress_dict)

            # Secrets
            secret_list = self._merge_secrets(
                [{"name": "acr-password", "value": self.parent.registry_password}],
                resource.get("secret", [])
            )
            secrets = [Secret(**secret_dict) for secret_dict in secret_list]

            # Registry
            registry_list = [{
                "server": f"{self.parent.registry_name}.azurecr.io",
                "username": self.parent.registry_name,
                "password_secret_name": "acr-password"
            }]
            registries = [Registry(**registry_dict) for registry_dict in registry_list]

            # Final Assembly
            ca = ContainerApp(
                container_app_environment_id=self.parent.azurerm_container_app_environment.azurerm_container_app_environment_id,
                name=ca_name,
                resource_group_name=self.parent.azurerm_resource_group.azurerm_resource_group_id,
                template=template,
                ingress=ingress,
                registry=registries,
                secret=secrets,
            )

            self.container_app_list.append(ca)

            resources[resource_name] = ca.dict()

    def get_resource_information(self, stack_id: str, iac: dict) -> dict:
        class ResourceInformation(BaseModel):
            resource_name: str = Field(default=RESOURCE_NAME)
            endpoint: str
            status: str
            is_persistent: bool

        class StackInformation(BaseModel):
            resources: List[ResourceInformation]

        response = {}
        stack_info = StackInformation(resources=[])

        for container in self.container_app_list:
            print(f"Processing container app: {container}")
            # Get container ingress endpoint
            response = self.parent.request(
                f"https://management.azure.com/subscriptions/{self.parent.subscription_id}/resourceGroups/{self.parent.azurerm_resource_group.azurerm_resource_group_id}/providers/Microsoft.App/containerApps/mern-backend-c17a810399e344a0?api-version=2023-05-01",
                "GET",
                None
            )

            endpoint = response.get("properties", {}).get("configuration", {}).get("ingress", {}).get("fqdn", "")
            status = response.get("properties", {}).get("provisioningState", "Unknown")
            is_persistent = container.template.min_replicas > 0

            stack_info.resources.append(ResourceInformation(endpoint=endpoint, status=status, is_persistent=is_persistent))

        return stack_info.model_dump()
            
    
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

def ensure_dict(obj: object, name: str) -> dict:
    if not isinstance(obj, dict):

        raise ValueError(f"{name} must be a dictionary")
    return obj

def ensure_list(obj: object, name: str) -> list:
    if not isinstance(obj, list):
        raise ValueError(f"{name} must be a list")
    return obj

