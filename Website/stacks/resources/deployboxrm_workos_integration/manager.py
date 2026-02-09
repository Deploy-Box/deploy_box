from .model import DeployBoxrmWorkOSIntegration, CLASS_PREFIX
from .serializer import DeployBoxrmWorkosIntegrationSerializer
from stacks.resources.resource_manager import ResourceManager

class DeployBoxrmWorkOSIntegrationManager(ResourceManager):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def get_model() -> type[DeployBoxrmWorkOSIntegration]:
        return DeployBoxrmWorkOSIntegration
    
    @staticmethod
    def serialize(resource: DeployBoxrmWorkOSIntegration) -> dict:
        return dict(DeployBoxrmWorkosIntegrationSerializer(resource).data)