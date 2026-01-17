from .model import AzurermResourceGroup, CLASS_PREFIX
from .serializer import AzurermResourceGroupSerializer
from stacks.resources.resource_manager import ResourceManager

class AzurermResourceGroupManager(ResourceManager):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def get_model() -> type[AzurermResourceGroup]:
        return AzurermResourceGroup
    
    @staticmethod
    def serialize(resource: AzurermResourceGroup) -> dict:
        return dict(AzurermResourceGroupSerializer(resource).data)