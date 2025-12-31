from django.db import models
import uuid


class ShortUUIDField(models.CharField):
    prefix = None

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 16
        kwargs["unique"] = True
        kwargs["editable"] = False
        self.prefix = kwargs.get("prefix")
        kwargs.pop("prefix", None)
        
        super().__init__(*args, **kwargs)

    def db_type(self, connection):
        return super().db_type(connection)

    def pre_save(self, model_instance, add):
        if add and not getattr(model_instance, self.attname):
            value = str(uuid.uuid4()).replace("-", "")[:16]
            if self.prefix:
                value = f"{self.prefix}_{value[:16 - len(self.prefix) - 1]}"
            setattr(model_instance, self.attname, value)
            return value
        return super().pre_save(model_instance, add)
