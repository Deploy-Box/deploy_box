from django.db import models

from core.fields import ShortUUIDField

TYPE_CHOICES = [
    ('RESOURCE', 'Resource'),
    ('DATA', 'Data'),
]

CLASS_PREFIX = "res000"

class AzurermResourceGroup(models.Model):
    id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)
    name = models.CharField(max_length=255)
    stack = models.ForeignKey('stacks.Stack', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Resource specific fields
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='RESOURCE')
    azurerm_id = models.CharField(max_length=255)
    azurerm_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, default='eastus')
    tags = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name