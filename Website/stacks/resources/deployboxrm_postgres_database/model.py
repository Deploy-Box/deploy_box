from django.db import models
from core.fields import ShortUUIDField
from stacks.resources.base_resource_model import BaseResourceModel

CLASS_PREFIX = "res00E"
RESOURCE_NAME = "deployboxrm_postgres_database"


class DeployBoxrmPostgresDatabase(BaseResourceModel):
    id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)

    # Reference to the deploy-box-postgres service record
    deploybox_database_id = models.CharField(max_length=255, blank=True, default="")

    # Connection details (populated after provisioning)
    db_host = models.CharField(max_length=255, default="deploy-box-postgres.postgres.database.azure.com")
    db_port = models.IntegerField(default=5432)
    db_name = models.CharField(max_length=255, blank=True, default="")
    db_user = models.CharField(max_length=255, blank=True, default="")
    db_password = models.CharField(max_length=255, blank=True, default="")
    connection_string = models.TextField(blank=True, default="")
    sslmode = models.CharField(max_length=32, default="require")

    # Metadata
    status = models.CharField(max_length=32, default="pending")
    region = models.CharField(max_length=64, default="eastus")
    display_name = models.CharField(max_length=255, blank=True, default="")

    class Meta(BaseResourceModel.Meta):
        pass

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = f"{RESOURCE_NAME}_{self.index}"
        if not self.display_name:
            self.display_name = f"Postgres Database {self.index}"
        super().save(*args, **kwargs)
