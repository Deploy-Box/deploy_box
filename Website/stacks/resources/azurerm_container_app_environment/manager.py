from .model import AzurermContainerAppEnvironment, CLASS_PREFIX
from .serializer import AzurermContainerAppEnvironmentSerializer
from stacks.resources.resource import Resource, create_filtered_data

class AzurermContainerAppEnvironmentManager(Resource):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def create(data: dict) -> AzurermContainerAppEnvironment:
        if "azurerm_name" not in data:
            data.update({"azurerm_name": data.get("name")})
            
        filtered_data = create_filtered_data(data, AzurermContainerAppEnvironment)
        
        return AzurermContainerAppEnvironment.objects.create(**filtered_data)
    
    @staticmethod
    def read(container_app_environment_id: str):
        instance = AzurermContainerAppEnvironment.objects.get(id=container_app_environment_id)
        return AzurermContainerAppEnvironmentSerializer(instance).data
    
    @staticmethod
    def serialize(resource: AzurermContainerAppEnvironment) -> dict:
        return dict(AzurermContainerAppEnvironmentSerializer(resource).data)