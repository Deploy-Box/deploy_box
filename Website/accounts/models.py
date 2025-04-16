from django.db import models
from django.contrib.auth.models import User
from core.fields import ShortUUIDField


class UserProfile(models.Model):
    id = ShortUUIDField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    birthdate = models.DateField()
    email_verification_token = models.CharField(max_length=256, null=True, blank=True)
    new_email = models.EmailField(null=True, blank=True)

    def __str__(self):
        return self.user.username
