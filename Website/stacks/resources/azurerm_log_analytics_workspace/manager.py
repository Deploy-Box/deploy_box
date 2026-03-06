from .model import AzurermLogAnalyticsWorkspace, CLASS_PREFIX
from .serializer import AzurermLogAnalyticsWorkspaceSerializer
from stacks.resources.resource_manager import ResourceManager

class AzurermLogAnalyticsWorkspaceManager(ResourceManager):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def get_model() -> type[AzurermLogAnalyticsWorkspace]:
        return AzurermLogAnalyticsWorkspace
    
    @staticmethod
    def serialize(resource: AzurermLogAnalyticsWorkspace) -> dict:
        return dict(AzurermLogAnalyticsWorkspaceSerializer(resource).data)
