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

class AuthUser(User):
    id: str
    user_profile: UserProfile

    def __init__(self, user: User, user_id: str, user_profile: UserProfile):
        super().__init__()
        self.__dict__.update(user.__dict__)
        self.id = user_id
        self.user_profile = user_profile
