from django.db import models

from core.fields import ShortUUIDField

TYPE_CHOICES = [
    ('RESOURCE', 'Resource'),
    ('DATA', 'Data'),
]

class AzurermResourceGroup(models.Model):
    id = ShortUUIDField(primary_key=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    azurerm_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    tags = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.type