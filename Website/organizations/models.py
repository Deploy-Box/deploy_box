from django.db import models
from django.contrib.auth.models import User
from core.fields import ShortUUIDField

class Organization(models.Model):
    id = ShortUUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class OrganizationMember(models.Model):
    id = ShortUUIDField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=50,
        default="member",
        choices=[
            ("admin", "Admin"),
            ("member", "Member"),
        ],
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.organization.name}"

