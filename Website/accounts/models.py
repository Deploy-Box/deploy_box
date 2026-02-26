from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from core.utils.generate_uuid import generate_uuid

class UserProfile(AbstractUser):
    id = models.CharField(
        primary_key=True,
        max_length=22,
        default=generate_uuid,
        editable=False
    )
    groups = models.ManyToManyField(
        Group,
        related_name="userprofile_set",  # <-- change this to something unique
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name="userprofile_set",  # <-- change this too
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )
    email_verification_token = models.CharField(max_length=256, null=True, blank=True)
    new_email = models.EmailField(null=True, blank=True)
    workos_user_id = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        unique=True,
        help_text="WorkOS user ID for SSO-authenticated users",
    )
    auth_provider = models.CharField(
        max_length=50,
        default="local",
        help_text="Authentication provider: local, workos, google, github",
    )

    def __str__(self):
        return self.username
