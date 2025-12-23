from .model import AzurermStorageContainer, CLASS_PREFIX
from .serializer import AzurermStorageContainerSerializer
from stacks.resources.resource_manager import ResourceManagerABC, create_filtered_data

class AzurermStorageContainerManager(ResourceManagerABC):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def create(data: dict) -> AzurermStorageContainer:
        if "azurerm_name" not in data:
            data.update({"azurerm_name": f'{data.get("stack").pk}sc'})
    
        filtered_data = create_filtered_data(data, AzurermStorageContainer)
        
        return AzurermStorageContainer.objects.create(**filtered_data)
    
    @staticmethod
    def read(storage_container_id: str):
        instance = AzurermStorageContainer.objects.get(id=storage_container_id)
        return AzurermStorageContainerSerializer(instance).data
    
    @staticmethod
    def serialize(resource: AzurermStorageContainer) -> dict:
        return AzurermStorageContainerSerializer(resource).data