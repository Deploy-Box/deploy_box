from .model import AzurermPublicIp, CLASS_PREFIX
from .serializer import AzurermPublicIpSerializer
from stacks.resources.resource_manager import ResourceManager

class AzurermPublicIpManager(ResourceManager):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def get_model() -> type[AzurermPublicIp]:
        return AzurermPublicIp
    
    @staticmethod
    def serialize(resource: AzurermPublicIp) -> dict:
        return dict(AzurermPublicIpSerializer(resource).data)
