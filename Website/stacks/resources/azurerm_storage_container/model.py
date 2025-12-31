from django.db import models

from core.fields import ShortUUIDField

TYPE_CHOICES = [
    ('RESOURCE', 'Resource'),
    ('DATA', 'Data'),
]

CONTAINER_ACCESS_TYPE_CHOICES = [
    ('private', 'Private'),
    ('blob', 'Blob'),
    ('container', 'Container'),
]

CLASS_PREFIX = "res003"

class AzurermStorageContainer(models.Model):
    id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='RESOURCE')
    stack = models.ForeignKey('stacks.Stack', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Resource specific fields
    azurerm_id = models.CharField(max_length=255)
    azurerm_name = models.CharField(max_length=255)
    storage_account_id = models.CharField(max_length=255)
    container_access_type = models.CharField(max_length=50, choices=CONTAINER_ACCESS_TYPE_CHOICES, default='private')
    default_encryption_scope = models.CharField(max_length=255, blank=True, default='')
    encryption_scope_override_enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name