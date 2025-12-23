from .model import AzurermResourceGroup, CLASS_PREFIX
from .serializer import AzurermResourceGroupSerializer
from stacks.resources.resource_manager import ResourceManagerABC, create_filtered_data

class AzurermResourceGroupManager(ResourceManagerABC):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def create(data: dict) -> AzurermResourceGroup:
        if "azurerm_name" not in data:
            data.update({"azurerm_name": f'{data.get("stack").pk}-rg'})

        if "location" not in data:
            data.update({"location": "eastus"})
    
        filtered_data = create_filtered_data(data, AzurermResourceGroup)
        
        return AzurermResourceGroup.objects.create(**filtered_data)
    
    @staticmethod
    def read(resource_group_id: str):
        instance = AzurermResourceGroup.objects.get(id=resource_group_id)
        return AzurermResourceGroupSerializer(instance).data
    
    @staticmethod
    def serialize(resource: AzurermResourceGroup) -> dict:
        return AzurermResourceGroupSerializer(resource).data