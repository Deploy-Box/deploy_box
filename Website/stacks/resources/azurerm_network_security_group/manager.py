from .model import AzurermNetworkSecurityGroup, CLASS_PREFIX
from .serializer import AzurermNetworkSecurityGroupSerializer
from stacks.resources.resource_manager import ResourceManager

class AzurermNetworkSecurityGroupManager(ResourceManager):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def get_model() -> type[AzurermNetworkSecurityGroup]:
        return AzurermNetworkSecurityGroup
    
    @staticmethod
    def serialize(resource: AzurermNetworkSecurityGroup) -> dict:
        return dict(AzurermNetworkSecurityGroupSerializer(resource).data)
