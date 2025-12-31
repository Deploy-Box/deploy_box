from .model import AzurermStorageAccount, CLASS_PREFIX
from .serializer import AzurermStorageAccountSerializer
from stacks.resources.resource_manager import ResourceManagerABC, create_filtered_data

class AzurermStorageAccountManager(ResourceManagerABC):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def create(data: dict) -> AzurermStorageAccount:
        if "azurerm_name" not in data:
            data.update({"azurerm_name": f'{data.get("stack").pk}sa'})
    
        filtered_data = create_filtered_data(data, AzurermStorageAccount)
        
        return AzurermStorageAccount.objects.create(**filtered_data)
    
    @staticmethod
    def read(resource_group_id: str):
        instance = AzurermStorageAccount.objects.get(id=resource_group_id)
        return AzurermStorageAccountSerializer(instance).data
    
    @staticmethod
    def serialize(resource: AzurermStorageAccount) -> dict:
        return AzurermStorageAccountSerializer(resource).data