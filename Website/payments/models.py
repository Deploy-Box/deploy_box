from django.db import models
from core.fields import ShortUUIDField

# Create your models here.

class Prices(models.Model):
    id = ShortUUIDField(primary_key=True)
    name = models.CharField(max_length=20)
    price = models.FloatField(default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
