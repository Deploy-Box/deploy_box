from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from cryptography.fernet import Fernet

from stacks.models import Stack
from core.fields import ShortUUIDField

ENCRYPTION_KEY = settings.GITHUB["TOKEN_KEY"]

if not ENCRYPTION_KEY:
    raise ValueError("GITHUB_TOKEN_KEY is not set")


class Webhook(models.Model):
    id = ShortUUIDField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Link webhook to a user
    stack = models.ForeignKey(
        Stack, on_delete=models.CASCADE
    )  # Link webhook to a stack
    repository = models.CharField(max_length=255)  # Repo name e.g., "username/repo"
    webhook_id = models.IntegerField(unique=True)  # GitHub's webhook ID
    url = models.URLField()  # Webhook callback URL
    secret = models.CharField(max_length=255)  # Webhook secret for verification
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Webhook for {self.repository} (User: {self.user.username})"


class Token(models.Model):
    id = ShortUUIDField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Link token to user
    encrypted_token = models.BinaryField()  # Store encrypted token

    def set_token(self, token: str):
        """Encrypt and store GitHub token."""
        assert isinstance(ENCRYPTION_KEY, str)
        cipher = Fernet(ENCRYPTION_KEY)
        token_string = str(token)
        encrypted_token = cipher.encrypt(token_string.encode())
        self.encrypted_token = encrypted_token

    def get_token(self) -> str:
        """Decrypt and return GitHub token."""
        assert isinstance(ENCRYPTION_KEY, str)
        cipher = Fernet(ENCRYPTION_KEY)
        bytes_token = bytes(self.encrypted_token)
        decrypted_token = cipher.decrypt(bytes_token)
        return decrypted_token.decode()

