from django.db import models

from core.fields import ShortUUIDField

TYPE_CHOICES = [
    ('RESOURCE', 'Resource'),
    ('DATA', 'Data'),
]

CLASS_PREFIX = "res001"

class AzurermContainerApp(models.Model):
    id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)
    name = models.CharField(max_length=255)
    stack = models.ForeignKey('stacks.Stack', on_delete=models.CASCADE)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='RESOURCE')
    azurerm_id = models.CharField(max_length=255)
    azurerm_name = models.CharField(max_length=255)
    resource_group_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.azurerm_name