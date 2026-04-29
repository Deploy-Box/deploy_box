from stacks.resources.resource_manager import ResourceManager
from .model import DeployBoxrmPostgresDatabase, CLASS_PREFIX
from .serializer import DeployBoxrmPostgresDatabaseSerializer


class DeployBoxrmPostgresDatabaseManager(ResourceManager):
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX

    @staticmethod
    def get_model() -> type[DeployBoxrmPostgresDatabase]:
        return DeployBoxrmPostgresDatabase

    @staticmethod
    def serialize(resource: DeployBoxrmPostgresDatabase) -> dict:
        return dict(DeployBoxrmPostgresDatabaseSerializer(resource).data)
