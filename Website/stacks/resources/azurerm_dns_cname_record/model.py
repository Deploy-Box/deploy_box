from django.db import models

from stacks.resources.resource import Resource
from core.fields import ShortUUIDField

TYPE_CHOICES = [
    ('RESOURCE', 'Resource'),
    ('DATA', 'Data'),
]

CLASS_PREFIX = "res005"

class AzurermDnsCnameRecord(Resource):
    id = ShortUUIDField(primary_key=True, prefix=CLASS_PREFIX)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='RESOURCE')
    stack = models.ForeignKey('stacks.Stack', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Resource specific fields
    azurerm_id = models.CharField(max_length=255)
    azurerm_name = models.CharField(max_length=255)
    fqdn = models.CharField(max_length=255)
    resource_group_name = models.CharField(max_length=255)
    zone_name = models.CharField(max_length=255)
    ttl = models.IntegerField(default=3600)
    record = models.CharField(max_length=255)
    tags = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        assert self.stack is not None, "Stack must be provided"
        assert isinstance(self.stack, models.Model), "Stack must be a valid Stack instance"

        if not self.azurerm_name:
            self.azurerm_name = f'{self.stack.pk}-cname'
            
        super().save(*args, **kwargs)
        
    @staticmethod
    def get_resource_prefix() -> str:
        return CLASS_PREFIX