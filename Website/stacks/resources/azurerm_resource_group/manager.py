from .model import AzurermResourceGroup, CLASS_PREFIX
from .serializer import AzurermResourceGroupSerializer
from stacks.resources.resource import Resource, create_filtered_data

class AzurermResourceGroupManager(Resource):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def read(resource_group_id: str):
        instance = AzurermResourceGroup.objects.get(id=resource_group_id)
        return AzurermResourceGroupSerializer(instance).data
    
    @staticmethod
    def serialize(resource: AzurermResourceGroup) -> dict:
        return dict(AzurermResourceGroupSerializer(resource).data)