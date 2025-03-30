from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    birthdate = models.DateField()
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    email_verification_token = models.CharField(max_length=256, null=True, blank=True)
    new_email = models.EmailField(null=True, blank=True)

    def __str__(self):
        return self.user.username
