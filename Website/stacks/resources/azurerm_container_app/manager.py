from .model import AzurermContainerApp, CLASS_PREFIX
from .serializer import AzurermContainerAppSerializer
from stacks.resources.resource_manager import ResourceManager

class AzurermContainerAppManager(ResourceManager):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def get_model() -> type[AzurermContainerApp]:
        return AzurermContainerApp
    
    @staticmethod
    def serialize(resource: AzurermContainerApp) -> dict:
        return dict(AzurermContainerAppSerializer(resource).data)