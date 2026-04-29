from .model import AzurermKeyVault, CLASS_PREFIX
from .serializer import AzurermKeyVaultSerializer
from stacks.resources.resource_manager import ResourceManager

class AzurermKeyVaultManager(ResourceManager):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def get_model() -> type[AzurermKeyVault]:
        return AzurermKeyVault
    
    @staticmethod
    def serialize(resource: AzurermKeyVault) -> dict:
        return dict(AzurermKeyVaultSerializer(resource).data)
