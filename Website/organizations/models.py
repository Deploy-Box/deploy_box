from django.db import models
from django.conf import settings

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

    def get_projects(self) -> list:
        from projects.models import Project

        return list(Project.objects.filter(organization=self))

class OrganizationMember(models.Model):
    id = ShortUUIDField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
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


class PendingInvites(models.Model):
    id = ShortUUIDField(primary_key=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    email = models.EmailField()

    def __str__(self):
        return self.email


