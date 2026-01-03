from .model import AzurermContainerApp, CLASS_PREFIX
from .serializer import AzurermContainerAppSerializer
from stacks.resources.resource import Resource, create_filtered_data

class AzurermContainerAppManager(Resource):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def create(data: dict) -> AzurermContainerApp:
        if "azurerm_name" not in data:
            data.update({"azurerm_name": data.get("name")})
            
        filtered_data = create_filtered_data(data, AzurermContainerApp)
        
        return AzurermContainerApp.objects.create(**filtered_data)
    
    @staticmethod
    def read(container_app_id: str):
        instance = AzurermContainerApp.objects.get(id=container_app_id)
        return AzurermContainerAppSerializer(instance).data
    
    @staticmethod
    def serialize(resource: AzurermContainerApp) -> dict:
        return dict(AzurermContainerAppSerializer(resource).data)