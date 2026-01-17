from .model import AzurermContainerAppEnvironment, CLASS_PREFIX
from .serializer import AzurermContainerAppEnvironmentSerializer
from stacks.resources.resource_manager import ResourceManager

class AzurermContainerAppEnvironmentManager(ResourceManager):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def get_model() -> type[AzurermContainerAppEnvironment]:
        return AzurermContainerAppEnvironment
    
    @staticmethod
    def serialize(resource: AzurermContainerAppEnvironment) -> dict:
        return dict(AzurermContainerAppEnvironmentSerializer(resource).data)