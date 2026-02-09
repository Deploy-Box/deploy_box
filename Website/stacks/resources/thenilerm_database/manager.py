from .model import TheNilermDatabase, CLASS_PREFIX
from .serializer import TheNilermDatabaseSerializer
from stacks.resources.resource_manager import ResourceManager

class TheNilermDatabaseManager(ResourceManager):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX
    
    @staticmethod
    def get_model() -> type[TheNilermDatabase]:
        return TheNilermDatabase
    
    @staticmethod
    def serialize(resource: TheNilermDatabase) -> dict:
        return dict(TheNilermDatabaseSerializer(resource).data)
    
