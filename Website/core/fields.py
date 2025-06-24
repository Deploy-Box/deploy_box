from django.db import models
import uuid


class ShortUUIDField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 16
        kwargs["unique"] = True
        kwargs["editable"] = False
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        if add and not getattr(model_instance, self.attname):
            # Generate a new UUID and take first 16 characters
            value = str(uuid.uuid4()).replace("-", "")[:16]
            setattr(model_instance, self.attname, value)
            return value
        return super().pre_save(model_instance, add)


if __name__ == "__main__":
    from datetime import datetime

    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(str(uuid.uuid4()).replace("-", "")[:16])
