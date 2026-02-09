from django.db import models

from .model import AzurermStorageContainer, CLASS_PREFIX
from .serializer import AzurermStorageContainerSerializer
from stacks.resources.resource_manager import ResourceManager

class AzurermStorageContainerManager(ResourceManager):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def get_model() -> type[AzurermStorageContainer]:
        return AzurermStorageContainer
    
    @staticmethod
    def serialize(resource: AzurermStorageContainer) -> dict:
        return dict(AzurermStorageContainerSerializer(resource).data)