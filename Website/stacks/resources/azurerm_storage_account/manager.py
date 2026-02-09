from .model import AzurermStorageAccount, CLASS_PREFIX
from .serializer import AzurermStorageAccountSerializer
from stacks.resources.resource_manager import ResourceManager

class AzurermStorageAccountManager(ResourceManager):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def get_model() -> type[AzurermStorageAccount]:
        return AzurermStorageAccount
    
    @staticmethod
    def serialize(resource: AzurermStorageAccount) -> dict:
        return dict(AzurermStorageAccountSerializer(resource).data)