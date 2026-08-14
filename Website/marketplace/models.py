from django.db import models
from accounts.models import UserProfile
from stacks.models import PurchasableStack
from core.fields import ShortUUIDField

class DeveloperProfile(models.Model):
    id = ShortUUIDField(primary_key=True)
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='developer_profile')
    specializations = models.ManyToManyField(PurchasableStack, related_name='experts', blank=True)
    
    tagline = models.CharField(max_length=255, help_text="Short professional headline", default="Tech Expert")
    bio = models.TextField(blank=True, help_text="Detailed professional bio")
    
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_available = models.BooleanField(default=True, verbose_name="Available for hire")
    
    website_url = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.tagline}"
