"""
Business-logic layer for the stacks app.

All functions here work with plain Python objects / Django models and raise
exceptions on failure.  They never touch ``HttpRequest`` / ``HttpResponse``.
"""

from __future__ import annotations

import logging
import json
import random
from dataclasses import dataclass
from typing import BinaryIO

import requests as http_requests
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from azure.storage.blob import BlobServiceClient
from azure.servicebus import ServiceBusClient, ServiceBusMessage

from projects.models import Project
from stacks.models import Stack, PurchasableStack
from stacks.resources.resources_manager import ResourcesManager, create_filtered_data

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB
ZIP_MAGIC_BYTES = b"PK\x03\x04"

_ADJECTIVES = [
    "Superb", "Incredible", "Fantastic", "Amazing", "Awesome",
    "Brilliant", "Exceptional", "Outstanding", "Remarkable",
    "Extraordinary", "Magnificent", "Spectacular", "Stunning", "Impressive",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class ServiceError(Exception):
    """Base exception for service-layer errors."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class ValidationError(ServiceError):
    """Raised when input validation fails."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, status_code)


class NotFoundError(ServiceError):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str = "Not found."):
        super().__init__(message, status_code=404)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------
@dataclass
class UploadResult:
    blob_name: str
    blob_url: str


# ---------------------------------------------------------------------------
# Stack CRUD
# ---------------------------------------------------------------------------
def create_stack(project_id: str, purchasable_stack_id: str) -> dict:
    """Create a new Stack, provision its resources, and enqueue an IAC.CREATE job.

    Returns the data dict sent to the queue (includes ``stack_id`` and ``resources``).
    Raises ``ValidationError`` / ``NotFoundError`` on bad input.
    """
    if not project_id:
        raise ValidationError("Project ID is required.")
    if not purchasable_stack_id:
        raise ValidationError("Purchasable Stack ID is required.")

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        raise NotFoundError("Project not found.")

    try:
        purchasable_stack = PurchasableStack.objects.get(pk=purchasable_stack_id)
    except PurchasableStack.DoesNotExist:
        raise NotFoundError("Purchasable Stack not found.")

    random_adjective = random.choice(_ADJECTIVES)
    stack_name = f"{random_adjective} {purchasable_stack.type} Stack"

    stack = Stack.objects.create(
        name=stack_name,
        project=project,
        purchased_stack=purchasable_stack,
    )

    created_resources = ResourcesManager.create(
        purchasable_stack.stack_infrastructure, stack
    )

    data = {
        "stack_id": stack.pk,
        "initial_source_code_zip_blob_name": "mobile.zip",
        "resources": ResourcesManager.serialize(created_resources),
    }

    send_to_queue("IAC.CREATE", data)
    return data


def delete_stack(stack_id: str) -> None:
    """Mark a stack for deletion by enqueuing an IAC.DELETE job.

    Raises ``NotFoundError`` if the stack does not exist.
    """
    try:
        stack = Stack.objects.get(pk=stack_id)
    except Stack.DoesNotExist:
        raise NotFoundError("Stack not found.")

    send_to_queue("IAC.DELETE", {"stack_id": stack.pk})


def trigger_iac_update(stack_id: str) -> dict:
    """Enqueue an IAC.UPDATE job for *stack_id*.

    Returns the data dict sent to the queue.
    Raises ``NotFoundError`` if the stack does not exist.
    """
    try:
        stack = Stack.objects.get(pk=stack_id)
    except Stack.DoesNotExist:
        raise NotFoundError("Stack not found.")

    resources = ResourcesManager.get_from_stack(stack)
    data = {
        "stack_id": stack.pk,
        "resources": ResourcesManager.serialize(resources),
    }

    # If a GitHub webhook is connected, include repo info so the IAC
    # container-app can pull source code directly from GitHub.
    github_data = _get_github_info_for_stack(stack)
    if github_data:
        data.update(github_data)

    if not send_to_queue("IAC.UPDATE", data):
        raise ServiceError("Failed to send IAC update to the service bus.")
    return data


def _get_github_info_for_stack(stack: Stack) -> dict | None:
    """Return GitHub repo/token info for *stack*, or ``None``.

    Looks up the most recent ``Webhook`` linked to the stack and resolves
    the owner's decrypted GitHub token.
    """
    from github.models import Webhook, Token

    webhook = (
        Webhook.objects
        .filter(stack=stack)
        .select_related("user")
        .order_by("-created_at")
        .first()
    )
    if webhook is None:
        return None

    try:
        token_obj = Token.objects.get(user=webhook.user)
        github_token = token_obj.get_token()
    except Token.DoesNotExist:
        logger.warning(
            "GitHub Token not found for user %s (stack %s); skipping GitHub source.",
            webhook.user_id,
            stack.pk,
        )
        return None

    return {
        "github_repo": webhook.repository,
        "github_token": github_token,
    }


# ---------------------------------------------------------------------------
# Bulk resource updates
# ---------------------------------------------------------------------------
def bulk_update_resources(resources_data: list[dict]) -> None:
    """Update a batch of resources in-place.

    Silently skips resources that cannot be found or that resolve to
    multiple objects.
    """
    for resource in resources_data:
        resource_id = resource.get("id")
        resource.pop("stack", None)

        if not resource_id:
            logger.warning("Resource entry missing 'id', skipping.")
            continue

        existing_resource = ResourcesManager.read(resource_id)
        if not existing_resource:
            logger.warning("Resource with ID %s not found.", resource_id)
            continue

        if isinstance(existing_resource, list):
            logger.warning(
                "Resource ID %s refers to multiple resources; expected a single resource.",
                resource_id,
            )
            continue

        existing_resource.__dict__.update(
            create_filtered_data(resource, type(existing_resource))
        )
        existing_resource.save()
        logger.info("Resource %s updated successfully.", resource_id)


# ---------------------------------------------------------------------------
# Traefik config
# ---------------------------------------------------------------------------
def get_traefik_config() -> dict:
    """Build the Traefik HTTP config for all tenant edge resources.

    Returns a dict suitable for JSON serialisation.
    """
    from stacks.resources.deployboxrm_edge.model import DeployBoxrmEdge

    base_domain = settings.BASE_DOMAIN
    edges = DeployBoxrmEdge.objects.all()

    routers: dict = {}
    svc: dict = {}
    middlewares: dict = {}

    for edge in edges:
        subdomain = edge.subdomain

        if edge.resolved_root_base_url:
            routers[f"{subdomain}-root"] = {
                "rule": f"Host(`{subdomain}.{base_domain}`)",
                "service": f"{subdomain}-root",
                "entryPoints": ["web"],
                "priority": 100,
            }
            svc[f"{subdomain}-root"] = {
                "loadBalancer": {
                    "servers": [{"url": edge.resolved_root_base_url}],
                    "passHostHeader": False,
                },
            }

        if edge.resolved_api_base_url:
            routers[f"{subdomain}-api"] = {
                "rule": f"Host(`{subdomain}.{base_domain}`) && PathPrefix(`/api`)",
                "service": f"{subdomain}-api",
                "middlewares": [f"{subdomain}-strip-api"],
                "entryPoints": ["web"],
                "priority": 200,
            }
            svc[f"{subdomain}-api"] = {
                "loadBalancer": {
                    "servers": [{"url": edge.resolved_api_base_url}],
                    "passHostHeader": False,
                },
            }
            middlewares[f"{subdomain}-strip-api"] = {
                "stripPrefix": {"prefixes": ["/api"]},
            }

    traefik_config = {
        "http": {
            "routers": routers,
            "services": svc,
        }
    }

    if middlewares:
        traefik_config["http"]["middlewares"] = middlewares

    return traefik_config


# ---------------------------------------------------------------------------
# Source-code download
# ---------------------------------------------------------------------------
def download_stack_source(stack_id: str) -> tuple[bytes, str]:
    """Download the source-code ZIP for *stack_id* from the configured endpoint.

    Returns ``(file_bytes, file_name)``.
    Raises ``NotFoundError`` if the stack doesn't exist and ``ServiceError``
    on configuration or network problems.
    """
    try:
        stack = Stack.objects.get(id=stack_id)
    except Stack.DoesNotExist:
        raise NotFoundError("Stack not found.")

    endpoint = getattr(settings, "DEPLOY_BOX_STACK_ENDPOINT", None)
    if not endpoint:
        raise ServiceError("DEPLOY_BOX_STACK_ENDPOINT is not configured.")

    file_name = (
        f"{stack.purchased_stack.type}-{stack.purchased_stack.variant}.zip".lower()
    )
    download_url = f"{endpoint.rstrip('/')}/{file_name}"

    try:
        response = http_requests.get(download_url, timeout=30)
        response.raise_for_status()
    except http_requests.RequestException as exc:
        logger.exception("Failed to download from %s", download_url)
        raise ServiceError(
            f"Failed to download file from configured endpoint: {exc}"
        )

    return response.content, file_name


# ---------------------------------------------------------------------------
# Source-code upload
# ---------------------------------------------------------------------------
def upload_source_code(uploaded_file: UploadedFile, stack_id: str) -> UploadResult:
    """Validate and upload *uploaded_file* to Azure Blob Storage.

    Returns an ``UploadResult`` on success.
    Raises ``ValidationError`` / ``NotFoundError`` / ``ServiceError`` on failure.
    """
    # 1. Validate the stack exists
    try:
        Stack.objects.get(id=stack_id)
    except Stack.DoesNotExist:
        raise NotFoundError("Stack not found.")

    # 2. Validate file size
    if uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
        limit_mb = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        actual_mb = round(uploaded_file.size / (1024 * 1024), 2)
        raise ValidationError(
            f"File too large ({actual_mb} MB). Maximum allowed size is {limit_mb} MB.",
            status_code=413,
        )

    # 3. Validate ZIP magic bytes
    header = uploaded_file.read(4)
    uploaded_file.seek(0)
    if header[:4] != ZIP_MAGIC_BYTES:
        raise ValidationError("Invalid file format. Only ZIP archives are accepted.")

    # 4. Verify Azure Blob client is available
    if BlobServiceClient is None:
        raise ServiceError("Azure Blob Storage client not available (missing package).")

    # 5. Read Azure configuration
    azure_cfg = getattr(settings, "AZURE", {})
    conn_str = azure_cfg.get("STORAGE_CONNECTION_STRING")
    container = azure_cfg.get("CONTAINER_NAME") or getattr(
        settings, "CONTAINER_NAME", None
    )
    if not conn_str or not container:
        raise ServiceError("Azure storage configuration missing.")

    # 6. Upload to Azure Blob Storage
    try:
        blob_service_client = BlobServiceClient.from_connection_string(conn_str)
        container_client = blob_service_client.get_container_client(container)

        blob_name = f"{stack_id}/user-files.zip"
        blob_client = container_client.get_blob_client(blob_name)

        file_stream = (
            uploaded_file.file if hasattr(uploaded_file, "file") else uploaded_file
        )
        blob_client.upload_blob(file_stream, overwrite=True)

        logger.info(
            "Source code uploaded for stack %s — blob: %s (%.2f MB)",
            stack_id,
            blob_name,
            uploaded_file.size / (1024 * 1024),
        )
    except Exception:
        logger.exception("Failed uploading source zip to Azure for stack %s", stack_id)
        raise ServiceError("Failed to upload file. Please try again.")

    return UploadResult(blob_name=blob_name, blob_url=blob_client.url)


# ---------------------------------------------------------------------------
# Azure Service Bus messaging
# ---------------------------------------------------------------------------
def send_to_queue(request_type: str, message_data: dict) -> bool:
    """Send a message to Azure Service Bus.

    Returns ``True`` on success, ``False`` on failure.
    """
    service_bus_connection_str = settings.AZURE_SERVICE_BUS.get("CONNECTION_STRING")
    queue_name = settings.AZURE_SERVICE_BUS.get("QUEUE_NAME")

    if not service_bus_connection_str or not queue_name:
        logger.error("Azure Service Bus configuration is missing.")
        return False

    data = {"request_type": request_type, "data": message_data}

    try:
        with ServiceBusClient.from_connection_string(
            service_bus_connection_str
        ) as client:
            with client.get_queue_sender(queue_name) as sender:
                message = ServiceBusMessage(json.dumps(data))
                sender.send_messages(message)
                logger.info(
                    "Successfully sent message to Azure Service Bus queue: %s",
                    queue_name,
                )
                return True
    except Exception as exc:
        logger.error("Failed to send message to Azure Service Bus: %s", exc)
        return False
