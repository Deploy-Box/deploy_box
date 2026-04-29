from .model import AzurermNetworkInterface, CLASS_PREFIX
from .serializer import AzurermNetworkInterfaceSerializer
from stacks.resources.resource_manager import ResourceManager

class AzurermNetworkInterfaceManager(ResourceManager):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def get_model() -> type[AzurermNetworkInterface]:
        return AzurermNetworkInterface
    
    @staticmethod
    def serialize(resource: AzurermNetworkInterface) -> dict:
        return dict(AzurermNetworkInterfaceSerializer(resource).data)
