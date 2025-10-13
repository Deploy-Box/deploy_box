from django.db import models
from core.fields import ShortUUIDField
from projects.models import Project

class API(models.Model):
    id = ShortUUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
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
