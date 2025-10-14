from django.db import models
from core.fields import ShortUUIDField
from projects.models import Project

class API(models.Model):
    id = ShortUUIDField(primary_key=True)
    api_key = models.CharField(max_length=128)
    name = models.CharField(max_length=255)
    description = models.TextField()
    price_per_1000_requests = models.DecimalField(max_digits=10, decimal_places=4)
    endpoint = models.CharField(max_length=255)
    icon = models.CharField(max_length=8)
    category = models.CharField(max_length=64)
    popular = models.BooleanField(default=False)
    response_time = models.CharField(max_length=32, blank=True)
    features = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class APICredential(models.Model):
    id = ShortUUIDField(primary_key=True)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='api_credential')
    client_id = models.CharField(max_length=128)
    client_secret = models.CharField(max_length=128)
    client_secret_hint = models.CharField(max_length=16, blank=True, help_text="Masked or partially revealed secret for display")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class APIUsage(models.Model):
    id = ShortUUIDField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='api_usages')
    api = models.ForeignKey(API, on_delete=models.CASCADE, related_name='usages')
    usage_count = models.IntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)