from .model import AzurermStorageAccountStaticWebsite, CLASS_PREFIX
from .serializer import AzurermStorageAccountStaticWebsiteSerializer
from stacks.resources.resource_manager import ResourceManager

class AzurermStorageAccountStaticWebsiteManager(ResourceManager):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def get_model() -> type[AzurermStorageAccountStaticWebsite]:
        return AzurermStorageAccountStaticWebsite
    
    @staticmethod
    def serialize(resource: AzurermStorageAccountStaticWebsite) -> dict:
        return dict(AzurermStorageAccountStaticWebsiteSerializer(resource).data)