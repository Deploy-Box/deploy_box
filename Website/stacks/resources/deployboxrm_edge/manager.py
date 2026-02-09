from .model import DeployBoxrmEdge, CLASS_PREFIX
from .serializer import DeployBoxrmEdgeSerializer
from stacks.resources.resource_manager import ResourceManager

class DeployBoxrmEdgeManager(ResourceManager):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def get_model() -> type[DeployBoxrmEdge]:
        return DeployBoxrmEdge
    
    def serialize(self, resource: DeployBoxrmEdge) -> dict:
        return dict(DeployBoxrmEdgeSerializer(resource).data)