from django.db import models
from django.contrib.auth.models import User
from cryptography.fernet import Fernet
from api.models import Stack
from core.fields import ShortUUIDField
import os
import json
from typing import Any

ENCRYPTION_KEY = os.getenv("GITHUB_TOKEN_KEY")

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


class WebhookEvent(models.Model):
    id = ShortUUIDField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Link event to a user
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE)  # Link event to a stack
    payload: Any = models.JSONField()  # Store entire webhook payload
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.received_at}"

    def get_pretty_payload(self):
        """Return a formatted JSON payload (for debugging in Django Admin)"""
        return json.dumps(self.payload, indent=4)


# Generate a secret key for encryption (run once and store securely)
# def generate_encryption_key():
#     return base64.urlsafe_b64encode(os.urandom(32))


class Token(models.Model):
    id = ShortUUIDField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Link token to user
    encrypted_token = models.BinaryField()  # Store encrypted token

    def set_token(self, token: str):
        """Encrypt and store GitHub token."""
        cipher = Fernet(ENCRYPTION_KEY)
        token_string = str(token)  # Ensure token is a string
        encrypted_token = cipher.encrypt(token_string.encode())
        self.encrypted_token = encrypted_token

    def get_token(self) -> str:
        """Decrypt and return GitHub token."""
        cipher = Fernet(ENCRYPTION_KEY)
        decrypted_token = cipher.decrypt(self.encrypted_token.tobytes())
        decoded_token = decrypted_token.decode()
        return decoded_token
