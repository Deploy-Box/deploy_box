from django.db import models

from .model import AzurermStorageContainer, CLASS_PREFIX
from .serializer import AzurermStorageContainerSerializer
from stacks.resources.resource import Resource, create_filtered_data

class AzurermStorageContainerManager(Resource):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def create(data: dict) -> AzurermStorageContainer:
        stack = data.get("stack")
        assert stack is not None, "Stack must be provided in data"
        assert isinstance(stack, models.Model), "Stack must be a valid Stack instance"

        if "azurerm_name" not in data:
            data.update({"azurerm_name": f'{stack.pk}-sc'})
    
        filtered_data = create_filtered_data(data, AzurermStorageContainer)
        
        return AzurermStorageContainer.objects.create(**filtered_data)
    
    @staticmethod
    def read(storage_container_id: str) -> dict:
        instance = AzurermStorageContainer.objects.get(id=storage_container_id)
        return dict(AzurermStorageContainerSerializer(instance).data)
    
    @staticmethod
    def serialize(resource: AzurermStorageContainer) -> dict:
        return dict(AzurermStorageContainerSerializer(resource).data)