"""
Deploy Box APIs service layer — business logic for API credential and key management.

Returns plain data (dicts) or raises ServiceError exceptions.
Never imports Response, JsonResponse, or HttpResponse.
"""
import hashlib
import json
import logging
import os
import secrets

import requests as http_requests
from django.utils import timezone

from deploy_box_apis.models import API, APICredential, APIKey, APIUsage
from projects.models import Project

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


class NotFoundError(ServiceError):
    def __init__(self, message="Not found"):
        super().__init__(message, status_code=404)


class ValidationError(ServiceError):
    def __init__(self, message="Invalid input"):
        super().__init__(message, status_code=400)


def _get_api_base_url() -> str:
    """Safely retrieve the Deploy Box API base URL from environment."""
    base_url = os.environ.get("DEPLOY_BOX_API_BASE_URL")
    if not base_url:
        raise ServiceError("DEPLOY_BOX_API_BASE_URL is not configured", status_code=500)
    return base_url.rstrip("/")


# ── OAuth Client Credentials ────────────────────────────────────────────────

def generate_credential(project_id: str) -> dict:
    """Generate API credentials for a project via the external Deploy Box API."""
    if not project_id:
        raise ValidationError("Project ID is required")

    existing = APICredential.objects.filter(project_id=project_id).first()
    if existing:
        return {
            "client_id": existing.client_id,
            "client_secret_hint": existing.client_secret_hint,
        }

    base_url = _get_api_base_url()
    response = http_requests.post(
        f"{base_url}/api/client_self_service/generate",
        json={"project_id": project_id},
    )
    if response.status_code != 200:
        raise ServiceError(f"Error generating API key: {response.text}")

    data = response.json()
    client_secret_hint = data["client_secret"][:4] + "..." + data["client_secret"][-4:]

    APICredential.objects.create(
        project_id=project_id,
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        client_secret_hint=client_secret_hint,
    )

    return {
        "client_id": data["client_id"],
        "client_secret": data["client_secret"],
        "client_secret_hint": client_secret_hint,
    }


def revoke_credential(project_id: str) -> dict:
    """Revoke API credentials for a project."""
    if not project_id:
        raise ValidationError("Project ID is required")

    existing = APICredential.objects.filter(project_id=project_id).first()
    if not existing:
        raise NotFoundError("No API key found for this project")

    base_url = _get_api_base_url()
    response = http_requests.post(
        f"{base_url}/api/client_self_service/revoke",
        json={"project_id": project_id},
    )
    if response.status_code not in (204, 404):
        raise ServiceError(f"Error revoking API key: {response.text}")

    existing.delete()
    return {"status": "API key revoked successfully"}


def rotate_credential(project_id: str) -> dict:
    """Rotate API credentials for a project."""
    if not project_id:
        raise ValidationError("Project ID is required")

    existing = APICredential.objects.filter(project_id=project_id).first()
    if not existing:
        raise NotFoundError("No API key found for this project")

    base_url = _get_api_base_url()
    response = http_requests.post(
        f"{base_url}/api/client_self_service/rotate",
        json={"project_id": project_id},
    )
    if response.status_code != 200:
        raise ServiceError(f"Error rotating API key: {response.text}")

    data = response.json()
    client_secret_hint = data["client_secret"][:4] + "..." + data["client_secret"][-4:]

    existing.client_id = data["client_id"]
    existing.client_secret = data["client_secret"]
    existing.client_secret_hint = client_secret_hint
    existing.save()

    return {
        "client_id": data["client_id"],
        "client_secret": data["client_secret"],
        "client_secret_hint": client_secret_hint,
    }


def generate_token(project_id: str) -> dict:
    """Generate an OAuth2 token for a project's API credentials."""
    if not project_id:
        raise ValidationError("Project ID is required")

    existing = APICredential.objects.filter(project_id=project_id).first()
    if not existing:
        raise NotFoundError("No API key found for this project")

    base_url = _get_api_base_url()
    response = http_requests.post(
        f"{base_url}/api/client_self_service/oauth2/token",
        json={
            "grant_type": "client_credentials",
            "client_id": existing.client_id,
            "client_secret": existing.client_secret,
        },
    )
    if response.status_code != 200:
        raise ServiceError(f"Error generating token: {response.text}")

    data = response.json()
    return {
        "access_token": data["access_token"],
        "token_type": data["token_type"],
        "expires_in": data["expires_in"],
    }


# ── Usage Tracking ───────────────────────────────────────────────────────────

def increment_usage(client_id: str, api_id: str) -> dict:
    """Increment usage count for an API by client credentials."""
    if not client_id or not api_id:
        raise ValidationError("client_id and api_id are required")

    credential = APICredential.objects.filter(client_id=client_id).first()
    if not credential:
        raise ValidationError("Invalid client_id")

    try:
        project = Project.objects.get(id=credential.project_id)
    except Project.DoesNotExist:
        raise NotFoundError(f"Project with ID {credential.project_id} does not exist")

    try:
        api = API.objects.get(api_key=api_id)
    except API.DoesNotExist:
        raise NotFoundError(f"API with ID {api_id} does not exist")

    api_usage, _ = APIUsage.objects.get_or_create(project=project, api=api)
    api_usage.usage_count += 1
    api_usage.last_used_at = timezone.now()
    api_usage.save()

    return {"usage_count": api_usage.usage_count}


# ── Public API Keys ──────────────────────────────────────────────────────────

def _generate_raw_key() -> str:
    """Generate a Google-style public API key: dbx_ + 40 URL-safe chars."""
    return "dbx_" + secrets.token_urlsafe(30)


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _key_hint(raw_key: str) -> str:
    return raw_key[:8] + "..." + raw_key[-4:]


def create_api_key(project_id: str, name: str = "Default") -> dict:
    """Generate a new public API key for a project."""
    if not project_id:
        raise ValidationError("project_id is required")

    raw_key = _generate_raw_key()
    api_key_obj = APIKey.objects.create(
        project_id=project_id,
        name=name,
        key_hash=_hash_key(raw_key),
        key_hint=_key_hint(raw_key),
    )

    return {
        "id": api_key_obj.id,
        "name": api_key_obj.name,
        "api_key": raw_key,
        "key_hint": api_key_obj.key_hint,
        "message": "Store this key securely — it will not be shown again.",
    }


def revoke_api_key(key_id: str, project_id: str) -> dict:
    """Revoke (deactivate) a public API key."""
    if not key_id or not project_id:
        raise ValidationError("key_id and project_id are required")

    api_key_obj = APIKey.objects.filter(id=key_id, project_id=project_id, is_active=True).first()
    if not api_key_obj:
        raise NotFoundError("API key not found or already revoked")

    api_key_obj.is_active = False
    api_key_obj.save()
    return {"status": "API key revoked"}


def list_api_keys(project_id: str) -> list[dict]:
    """List all API keys for a project."""
    if not project_id:
        raise ValidationError("project_id query param is required")

    keys = APIKey.objects.filter(project_id=project_id).values(
        "id", "name", "key_hint", "is_active", "created_at"
    )
    return list(keys)


def validate_api_key(raw_key: str) -> dict:
    """Validate a public API key. Returns project info if valid."""
    if not raw_key:
        raise ValidationError("api_key is required")

    key_hash = _hash_key(raw_key)
    api_key_obj = APIKey.objects.filter(
        key_hash=key_hash, is_active=True
    ).select_related("project").first()

    if not api_key_obj:
        return {"valid": False}

    return {
        "valid": True,
        "project_id": api_key_obj.project_id,
        "key_id": api_key_obj.id,
        "key_name": api_key_obj.name,
    }
