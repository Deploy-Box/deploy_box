from __future__ import annotations

from django.db import models
from abc import abstractmethod, ABC

class ResourceManager(ABC):
    @staticmethod
    @abstractmethod
    def get_resource_prefix() -> str:
        pass

    @staticmethod
    @abstractmethod
    def get_model() -> type[models.Model]:
        pass
    
    @staticmethod
    @abstractmethod
    def serialize(resource: models.Model) -> dict:
        raise NotImplementedError("serialize method must be implemented by subclasses")
