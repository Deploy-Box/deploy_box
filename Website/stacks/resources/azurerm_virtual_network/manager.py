from .model import AzurermVirtualNetwork, CLASS_PREFIX
from .serializer import AzurermVirtualNetworkSerializer
from stacks.resources.resource_manager import ResourceManager

class AzurermVirtualNetworkManager(ResourceManager):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def get_model() -> type[AzurermVirtualNetwork]:
        return AzurermVirtualNetwork
    
    @staticmethod
    def serialize(resource: AzurermVirtualNetwork) -> dict:
        return dict(AzurermVirtualNetworkSerializer(resource).data)
