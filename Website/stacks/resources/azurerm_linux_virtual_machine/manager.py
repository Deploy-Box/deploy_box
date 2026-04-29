from .model import AzurermLinuxVirtualMachine, CLASS_PREFIX
from .serializer import AzurermLinuxVirtualMachineSerializer
from stacks.resources.resource_manager import ResourceManager

class AzurermLinuxVirtualMachineManager(ResourceManager):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def get_model() -> type[AzurermLinuxVirtualMachine]:
        return AzurermLinuxVirtualMachine
    
    @staticmethod
    def serialize(resource: AzurermLinuxVirtualMachine) -> dict:
        return dict(AzurermLinuxVirtualMachineSerializer(resource).data)
