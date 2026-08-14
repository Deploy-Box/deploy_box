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
from datetime import timedelta
from typing import BinaryIO

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import models, transaction
from django.db.models import F
from django.db.models.functions import Concat
from django.utils import timezone

from azure.storage.blob import BlobServiceClient
from azure.servicebus import ServiceBusClient, ServiceBusMessage

from projects.models import Project
from organizations.models import OrganizationMember

from stacks.models import Stack, PurchasableStack, DeploymentLog, Operation
from stacks.resources.resources_manager import ResourcesManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB
ZIP_MAGIC_BYTES = b"PK\x03\x04"

CUSTOM_STACK_TYPE = "CUSTOM"

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


class ForbiddenError(ServiceError):
    """Raised when the user does not have permission."""

    def __init__(self, message: str = "Forbidden."):
        super().__init__(message, status_code=403)


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
def verify_project_access(user, project_id: str):
    """Validate user belongs to the organization that owns this project.

    Raises NotFoundError if project doesn't exist or user has no access.
    """
    from projects.models import Project
    try:
        project = Project.objects.select_related("organization").get(pk=project_id)
    except Project.DoesNotExist:
        raise NotFoundError("Project not found.")

    if not OrganizationMember.objects.filter(
        user=user, organization_id=project.organization_id
    ).exists():
        raise NotFoundError("Project not found.")

    return project


def create_stack(project_id: str, purchasable_stack_id: str, user=None) -> dict:
    """Create a new Stack, provision its resources, and enqueue an IAC.APPLY job.

    Returns the data dict sent to the queue (includes ``stack_id`` and ``resources``).
    Raises ``ValidationError`` / ``NotFoundError`` on bad input.
    """
    if not project_id:
        raise ValidationError("Project ID is required.")
    if not purchasable_stack_id:
        raise ValidationError("Purchasable Stack ID is required.")

    if user:
        project = verify_project_access(user, project_id)
    else:
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            raise NotFoundError("Project not found.")

    # Enforce free-tier stack limit
    if project.organization.has_reached_free_stack_limit():
        raise ValidationError(
            "Free plan is limited to 3 stacks per organization. "
            "Please upgrade to create more stacks."
        )

    # Require a payment method before the first stack
    from payments.services import organization_has_payment_method
    if not organization_has_payment_method(project.organization):
        raise ValidationError(
            "A payment method is required before creating a stack. "
            "Please add a card on the billing page."
        )

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
        "initial_source_code_zip_blob_name": purchasable_stack.source_code_location or "",
        "resources": ResourcesManager.serialize(created_resources),
    }

    operation = create_operation(str(stack.pk), "APPLY")
    send_to_queue("IAC.APPLY", data, operation_id=str(operation.id))
    return data


def create_custom_stack(project_id: str, user=None) -> dict:
    """Create an empty custom stack that the user can populate resource-by-resource.

    Returns the serialized stack data.
    Raises ``ValidationError`` / ``NotFoundError`` on bad input.
    """
    if not project_id:
        raise ValidationError("Project ID is required.")

    if user:
        project = verify_project_access(user, project_id)
    else:
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            raise NotFoundError("Project not found.")

    # Enforce free-tier stack limit
    if project.organization.has_reached_free_stack_limit():
        raise ValidationError(
            "Free plan is limited to 3 stacks per organization. "
            "Please upgrade to create more stacks."
        )

    # Require a payment method before the first stack
    from payments.services import organization_has_payment_method
    if not organization_has_payment_method(project.organization):
        raise ValidationError(
            "A payment method is required before creating a stack. "
            "Please add a card on the billing page."
        )

    purchasable_stack, _created = PurchasableStack.objects.get_or_create(
        type=CUSTOM_STACK_TYPE,
        variant="CUSTOM",
        version="1.0",
        defaults={
            "name": "Custom Stack",
            "description": "Build your own stack by adding individual resources.",
            "price_id": "",
            "features": ["Fully customisable", "Add any resource", "Pay per resource"],
            "stack_infrastructure": [],
        },
    )

    random_adjective = random.choice(_ADJECTIVES)
    stack_name = f"{random_adjective} Custom Stack"

    stack = Stack.objects.create(
        name=stack_name,
        project=project,
        purchased_stack=purchasable_stack,
        status="DRAFT",
    )

    from stacks.serializers import StackSerializer
    return StackSerializer(stack).data


def add_resource_to_stack(stack_id: str, resource_type: str, config: dict | None = None) -> dict:
    """Add a single resource to an existing stack.

    Returns the serialized resource.
    Raises ``NotFoundError`` if the stack doesn't exist,
    ``ValidationError`` if the resource type is unknown.
    """
    try:
        stack = Stack.objects.get(pk=stack_id)
    except Stack.DoesNotExist:
        raise NotFoundError("Stack not found.")

    try:
        resource = ResourcesManager.add_resource(stack, resource_type, config)
    except ValueError as exc:
        raise ValidationError(str(exc))

    serialized = ResourcesManager.serialize(resource)
    return serialized


def remove_resource_from_stack(stack_id: str, resource_id: str) -> None:
    """Remove a single resource from a stack.

    Raises ``NotFoundError`` if the stack or resource doesn't exist,
    ``ValidationError`` if the resource doesn't belong to the stack.
    """
    try:
        stack = Stack.objects.get(pk=stack_id)
    except Stack.DoesNotExist:
        raise NotFoundError("Stack not found.")

    resource = ResourcesManager.read(resource_id)
    if resource is None:
        raise NotFoundError(f"Resource {resource_id} not found.")

    if str(resource.stack_id) != str(stack.pk):
        raise ValidationError("Resource does not belong to this stack.")

    resource.delete()


def list_stack_resources(stack_id: str) -> list[dict]:
    """Return all resources belonging to a stack, serialized.

    Uses the unified Resource table when USE_UNIFIED_RESOURCE_READS is True
    (single query instead of 17). Output format is identical either way.

    Raises ``NotFoundError`` if the stack doesn't exist.
    """
    try:
        stack = Stack.objects.get(pk=stack_id)
    except Stack.DoesNotExist:
        raise NotFoundError("Stack not found.")

    resources = ResourcesManager.get_from_stack(stack)
    return ResourcesManager.serialize(resources)


def list_available_resource_types() -> list[dict]:
    """Return the catalogue of resource types that can be added to a stack."""
    return ResourcesManager.get_available_resource_types()


def delete_stack(stack_id: str) -> None:
    """Mark a stack for deletion by enqueuing an IAC.DELETE job.

    Raises ``NotFoundError`` if the stack does not exist.
    """
    try:
        stack = Stack.objects.get(pk=stack_id)
    except Stack.DoesNotExist:
        raise NotFoundError("Stack not found.")

    send_to_queue("IAC.DELETE", {"stack_id": stack.pk},
                  operation_id=str(create_operation(str(stack.pk), "DELETE").id))


def trigger_iac_update(stack_id: str) -> dict:
    """Enqueue an IAC.APPLY job for *stack_id*.

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

    operation = create_operation(str(stack.pk), "APPLY")
    if not send_to_queue("IAC.APPLY", data, operation_id=str(operation.id)):
        raise ServiceError("Failed to send IAC apply to the service bus.")
    return data


def pause_stack(stack_id: str) -> None:
    """Enqueue an IAC.PAUSE job to scale the stack's resources to zero.

    Raises ``NotFoundError`` if the stack does not exist.
    Raises ``ValidationError`` if the stack is not in a pausable state.
    """
    try:
        stack = Stack.objects.get(pk=stack_id)
    except Stack.DoesNotExist:
        raise NotFoundError("Stack not found.")

    if stack.status not in ("Ready",):
        raise ValidationError(
            f"Stack must be in 'Ready' status to pause (current: {stack.status})."
        )

    resources = ResourcesManager.get_from_stack(stack)
    data = {
        "stack_id": stack.pk,
        "resources": ResourcesManager.serialize(resources),
    }

    operation = create_operation(str(stack.pk), "PAUSE")
    if not send_to_queue("IAC.PAUSE", data, operation_id=str(operation.id)):
        raise ServiceError("Failed to send IAC pause to the service bus.")


def resume_stack(stack_id: str) -> None:
    """Enqueue an IAC.RESUME job to restore the stack's resources from pause.

    Raises ``NotFoundError`` if the stack does not exist.
    Raises ``ValidationError`` if the stack is not paused.
    """
    try:
        stack = Stack.objects.get(pk=stack_id)
    except Stack.DoesNotExist:
        raise NotFoundError("Stack not found.")

    if stack.status not in ("Paused",):
        raise ValidationError(
            f"Stack must be in 'Paused' status to resume (current: {stack.status})."
        )

    resources = ResourcesManager.get_from_stack(stack)
    data = {
        "stack_id": stack.pk,
        "resources": ResourcesManager.serialize(resources),
    }

    operation = create_operation(str(stack.pk), "RESUME")
    if not send_to_queue("IAC.RESUME", data, operation_id=str(operation.id)):
        raise ServiceError("Failed to send IAC resume to the service bus.")


def check_and_auto_pause_stacks() -> dict:
    """Check all organizations and pause stacks that exceed their credit allowance.

    Returns a summary dict: ``{"paused": [<stack_ids>], "errors": [<messages>]}``.
    Called periodically by the crontainer credit-check job.
    """
    from decimal import Decimal
    from django.utils import timezone
    from django.db.models import Sum
    from organizations.models import Organization
    from payments.models import MetricUsageRecord

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    paused_ids: list[str] = []
    errors: list[str] = []

    orgs = Organization.objects.filter(auto_pause_on_limit=True)
    for org in orgs:
        allowance = org.monthly_credit_allowance
        if allowance is None or allowance <= 0:
            continue

        org_stacks = Stack.objects.filter(project__organization=org)

        # Total dollar amount billed this month (sum of instance_usage_bill_amount)
        month_cost = org_stacks.aggregate(
            total=Sum("instance_usage_bill_amount")
        )["total"] or Decimal("0.00")

        if month_cost < allowance:
            continue

        # Over limit — pause all Ready stacks for this org
        ready_stacks = org_stacks.filter(status="Ready")
        for stack in ready_stacks:
            try:
                pause_stack(stack.pk)
                paused_ids.append(stack.pk)
                logger.info(
                    "Auto-paused stack %s (org %s): cost $%s exceeds allowance $%s",
                    stack.pk, org.pk, month_cost, allowance,
                )
            except Exception as exc:
                msg = f"Failed to auto-pause stack {stack.pk}: {exc}"
                logger.error(msg)
                errors.append(msg)

    return {"paused": paused_ids, "errors": errors}


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

    Uses ``ResourcesManager.update_resource()`` which maps flat IaC callback
    fields to the unified Resource model (promoted columns + attributes).
    Silently skips resources that cannot be found.
    """
    for resource in resources_data:
        resource_id = resource.get("id")
        resource.pop("stack", None)

        if not resource_id:
            logger.warning("Resource entry missing 'id', skipping.")
            continue

        updated = ResourcesManager.update_resource(resource_id, resource)
        if updated:
            logger.info("Resource %s updated successfully.", resource_id)
        else:
            logger.warning("Resource with ID %s not found.", resource_id)


# ---------------------------------------------------------------------------
# Traefik config
# ---------------------------------------------------------------------------
def get_traefik_config() -> dict:
    """Build the Traefik HTTP config for all tenant edge resources.

    Returns a dict suitable for JSON serialisation.
    """
    from stacks.resources.resource import Resource

    base_domain = settings.BASE_DOMAIN
    edges = Resource.objects.filter(resource_type="deployboxrm_edge")

    routers: dict = {}
    svc: dict = {}
    middlewares: dict = {}

    for edge in edges:
        attrs = edge.attributes or {}
        subdomain = attrs.get("subdomain", "")
        resolved_root_base_url = attrs.get("resolved_root_base_url", "")
        resolved_api_base_url = attrs.get("resolved_api_base_url", "")

        if not subdomain:
            continue

        if resolved_root_base_url:
            routers[f"{subdomain}-root"] = {
                "rule": f"Host(`{subdomain}.{base_domain}`)",
                "service": f"{subdomain}-root",
                "entryPoints": ["web"],
                "priority": 100,
            }
            svc[f"{subdomain}-root"] = {
                "loadBalancer": {
                    "servers": [{"url": resolved_root_base_url}],
                    "passHostHeader": False,
                },
            }

        if resolved_api_base_url:
            routers[f"{subdomain}-api"] = {
                "rule": f"Host(`{subdomain}.{base_domain}`) && PathPrefix(`/api`)",
                "service": f"{subdomain}-api",
                "middlewares": [f"{subdomain}-strip-api"],
                "entryPoints": ["web"],
                "priority": 200,
            }
            svc[f"{subdomain}-api"] = {
                "loadBalancer": {
                    "servers": [{"url": resolved_api_base_url}],
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
    """Download the source-code ZIP for *stack_id* from Azure Blob Storage.

    Returns ``(file_bytes, file_name)``.
    Raises ``NotFoundError`` if the stack doesn't exist and ``ServiceError``
    on configuration or network problems.
    """
    try:
        stack = Stack.objects.get(id=stack_id)
    except Stack.DoesNotExist:
        raise NotFoundError("Stack not found.")

    azure_cfg = getattr(settings, "AZURE", {})
    conn_str = azure_cfg.get("STORAGE_CONNECTION_STRING")
    container = azure_cfg.get("CONTAINER_NAME")
    if not conn_str or not container:
        raise ServiceError("Azure storage configuration missing.")

    file_name = (
        f"{stack.purchased_stack.type}-{stack.purchased_stack.variant}.zip".lower()
    )

    try:
        container_client = (
            BlobServiceClient.from_connection_string(conn_str)
            .get_container_client(container)
        )
        download_stream = container_client.download_blob(file_name)
        file_bytes = download_stream.readall()
    except Exception as exc:
        logger.exception("Failed to download blob %s from %s", file_name, container)
        raise ServiceError(
            f"Failed to download file from Azure Blob Storage: {exc}"
        )

    return file_bytes, file_name


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
def send_to_queue(request_type: str, message_data: dict, operation_id: str | None = None) -> bool:
    """Send a message to Azure Service Bus.

    When *operation_id* is provided it is included at the top level of the
    message payload so the IaC job can track which operation it is processing.

    Returns ``True`` on success, ``False`` on failure.
    """
    service_bus_connection_str = settings.AZURE_SERVICE_BUS.get("CONNECTION_STRING")
    queue_name = settings.AZURE_SERVICE_BUS.get("QUEUE_NAME")

    if not service_bus_connection_str or not queue_name:
        logger.error("Azure Service Bus configuration is missing.")
        return False

    data: dict = {
        "schema_version": 2,
        "request_type": request_type,
        "data": message_data,
    }
    if operation_id:
        data["operation_id"] = operation_id

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


# ---------------------------------------------------------------------------
# IAC deployment helper
# ---------------------------------------------------------------------------
class DeployBoxIAC:
    """Triggers IAC deployment via the Azure Service Bus."""

    def deploy(self, stack_id: str, resource_group: str, iac_state: dict) -> None:
        operation = create_operation(stack_id, "DEPLOY")
        if not send_to_queue("IAC.DEPLOY", {
            "resource_group": resource_group,
            "iac_state": iac_state,
        }, operation_id=str(operation.id)):
            raise ServiceError("Failed to send deployment to service bus.")


# ---------------------------------------------------------------------------
# Stack IAC / status helpers
# ---------------------------------------------------------------------------
def overwrite_stack_iac(stack_id: str, new_iac_state: dict) -> dict:
    """Overwrite the IAC state and trigger deployment.

    Returns a result dict on success.
    Raises ``NotFoundError`` if the stack does not exist.
    """
    try:
        stack = Stack.objects.get(pk=stack_id)
    except Stack.DoesNotExist:
        raise NotFoundError("Stack not found")

    old_iac = dict(stack.iac_state)
    stack.iac_state = new_iac_state
    stack.save()

    deployer = DeployBoxIAC()
    deployer.deploy(str(stack.pk), f"{stack.id}-rg", new_iac_state)

    return {
        "success": True,
        "message": "IAC configuration overwritten successfully",
        "stack_id": str(stack.id),
        "old_iac": old_iac,
        "new_iac": new_iac_state,
    }


def update_stack_status(stack_id: str, new_status: str) -> bool:
    """Update a stack's status.  Returns ``True`` on success, ``False`` on failure."""
    try:
        stack = Stack.objects.get(pk=stack_id)
        stack.status = new_status
        stack.save()
        return True
    except Exception:
        return False


def update_stack_iac_only(stack_id: str, new_iac_state: dict) -> bool:
    """Update IAC state without triggering deployment.  Returns ``True`` on success."""
    try:
        stack = Stack.objects.get(pk=stack_id)
        stack.iac_state = new_iac_state
        stack.save()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Deployment Logs
# ---------------------------------------------------------------------------
MAX_DEPLOYMENT_LOGS_PER_STACK = 10


def create_deployment_log(stack_id: str, operation: str) -> dict:
    """Create a new deployment log for a stack and prune old completed logs.

    Returns a dict with the new log's ``id`` and ``operation``.
    Raises ``NotFoundError`` / ``ValidationError`` on bad input.
    """
    try:
        stack = Stack.objects.get(pk=stack_id)
    except Stack.DoesNotExist:
        raise NotFoundError("Stack not found.")

    valid_operations = {c[0] for c in DeploymentLog.OPERATION_CHOICES}
    if operation not in valid_operations:
        raise ValidationError(f"Invalid operation: {operation}")

    log = DeploymentLog.objects.create(stack=stack, operation=operation)

    _cleanup_old_deployment_logs(stack_id)

    return {"id": str(log.id), "operation": log.operation, "status": log.status}


def append_deployment_log(log_id: str, text: str) -> bool:
    """Atomically append text to a deployment log.

    Uses ``Concat`` + ``F()`` for a single UPDATE query — safe under
    concurrent reads with no read-modify-write race.  Returns ``True``
    on success, ``False`` if the log doesn't exist or isn't RUNNING.
    """
    if not text:
        return True

    new_lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    if not text.endswith("\n"):
        text += "\n"

    updated = DeploymentLog.objects.filter(
        pk=log_id, status="RUNNING"
    ).update(
        log_text=Concat(F("log_text"), models.Value(text)),
        line_count=F("line_count") + new_lines,
    )
    return updated > 0


def complete_deployment_log(log_id: str, final_status: str = "COMPLETED") -> bool:
    """Mark a deployment log as completed or failed.

    Returns ``True`` on success.
    """
    if final_status not in ("COMPLETED", "FAILED"):
        raise ValidationError(f"Invalid final status: {final_status}")

    updated = DeploymentLog.objects.filter(
        pk=log_id, status="RUNNING"
    ).update(
        status=final_status,
        completed_at=timezone.now(),
    )
    return updated > 0


def get_latest_deployment_log(stack_id: str):
    """Return the most recent deployment log for a stack, or ``None``."""
    log = (
        DeploymentLog.objects
        .filter(stack_id=stack_id)
        .order_by("-started_at")
        .first()
    )
    if not log:
        return None

    return {
        "id": str(log.id),
        "operation": log.operation,
        "status": log.status,
        "line_count": log.line_count,
        "started_at": log.started_at.isoformat(),
        "completed_at": log.completed_at.isoformat() if log.completed_at else None,
    }


def get_deployment_log_content(log_id: str, after_line: int = 0):
    """Return a deployment log's content, optionally from a line offset.

    Returns ``None`` if the log doesn't exist.  The ``lines`` key contains
    only lines after the given offset for efficient polling.
    """
    log = DeploymentLog.objects.filter(pk=log_id).first()
    if not log:
        return None

    all_lines = log.log_text.split("\n") if log.log_text else []
    # Remove trailing empty string from final newline
    if all_lines and all_lines[-1] == "":
        all_lines = all_lines[:-1]

    new_lines = all_lines[after_line:] if after_line < len(all_lines) else []

    return {
        "id": str(log.id),
        "operation": log.operation,
        "status": log.status,
        "line_count": len(all_lines),
        "after_line": after_line,
        "lines": new_lines,
        "started_at": log.started_at.isoformat(),
        "completed_at": log.completed_at.isoformat() if log.completed_at else None,
    }


def _cleanup_old_deployment_logs(stack_id: str) -> int:
    """Delete completed/failed deployment logs beyond the retention limit.

    Never deletes RUNNING logs.  Returns the number of logs deleted.
    """
    completed_log_ids = list(
        DeploymentLog.objects
        .filter(stack_id=stack_id, status__in=["COMPLETED", "FAILED"])
        .order_by("-started_at")
        .values_list("id", flat=True)
    )

    ids_to_delete = completed_log_ids[MAX_DEPLOYMENT_LOGS_PER_STACK:]
    if not ids_to_delete:
        return 0

    deleted, _ = DeploymentLog.objects.filter(id__in=ids_to_delete).delete()
    return deleted


# ---------------------------------------------------------------------------
# Operations — lifecycle management
# ---------------------------------------------------------------------------
DEFAULT_LEASE_SECONDS = 1800  # 30 minutes


def create_operation(stack_id: str, operation_type: str) -> Operation:
    """Create a new PENDING operation for a stack.

    Does NOT check for running operations — that is the job's responsibility
    when it claims the operation. This allows queuing multiple operations.
    """
    try:
        stack = Stack.objects.get(pk=stack_id)
    except Stack.DoesNotExist:
        raise NotFoundError("Stack not found.")

    valid_types = {c[0] for c in Operation.OPERATION_CHOICES}
    if operation_type not in valid_types:
        raise ValidationError(f"Invalid operation type: {operation_type}")

    return Operation.objects.create(stack=stack, operation_type=operation_type)


def claim_operation(operation_id: str, attempt_id: str, lease_duration_seconds: int = DEFAULT_LEASE_SECONDS) -> dict:
    """Atomically claim a PENDING operation for processing.

    This uses a single atomic UPDATE + stack-level serialization to prevent
    concurrent operations on the same stack. The caller must provide a unique
    *attempt_id* to prove ownership during completion.

    Returns a dict with claim result on success.
    Raises ``NotFoundError`` if the operation doesn't exist.
    Raises ``ValidationError`` if the operation can't be claimed (already
    claimed, or another operation is running on the same stack).
    """
    now = timezone.now()
    lease_expires = now + timedelta(seconds=lease_duration_seconds)

    with transaction.atomic():
        try:
            op = Operation.objects.select_for_update().get(pk=operation_id)
        except Operation.DoesNotExist:
            raise NotFoundError("Operation not found.")

        if op.status != 'PENDING':
            raise ValidationError(
                f"Operation is not claimable (current status: {op.status}).",
                status_code=409,
            )

        # Check no other RUNNING operation exists on the same stack.
        # Also check this is the oldest pending op — enforce ordering.
        running_exists = Operation.objects.filter(
            stack=op.stack, status='RUNNING',
        ).exists()
        if running_exists:
            raise ValidationError(
                "Another operation is already running on this stack.",
                status_code=409,
            )

        older_pending = Operation.objects.filter(
            stack=op.stack, status='PENDING', created_at__lt=op.created_at,
        ).exists()
        if older_pending:
            raise ValidationError(
                "An older pending operation must be processed first.",
                status_code=409,
            )

        # Claim it
        op.status = 'RUNNING'
        op.attempt_id = attempt_id
        op.started_at = now
        op.lease_expires_at = lease_expires
        op.save()

    return {
        "operation_id": str(op.id),
        "stack_id": str(op.stack_id),
        "operation_type": op.operation_type,
        "lease_expires_at": lease_expires.isoformat(),
    }


def complete_operation(operation_id: str, attempt_id: str, status: str, error_message: str = '') -> dict:
    """Mark a RUNNING operation as SUCCEEDED or FAILED.

    The *attempt_id* must match the one used during claim to prevent stale
    completions from overwriting newer state. On success, the stack status
    is updated atomically based on the operation type.

    Returns a dict with the final operation state.
    """
    if status not in ('SUCCEEDED', 'FAILED'):
        raise ValidationError(f"Invalid completion status: {status}")

    now = timezone.now()

    with transaction.atomic():
        try:
            op = Operation.objects.select_for_update().get(pk=operation_id)
        except Operation.DoesNotExist:
            raise NotFoundError("Operation not found.")

        if op.status != 'RUNNING':
            raise ValidationError(
                f"Operation is not completable (current status: {op.status}).",
                status_code=409,
            )

        if op.attempt_id != attempt_id:
            raise ValidationError(
                "attempt_id does not match the claiming worker.",
                status_code=409,
            )

        op.status = status
        op.error_message = error_message
        op.completed_at = now
        op.save()

        # Derive stack status from operation type + result (not from worker input)
        if status == 'SUCCEEDED':
            new_stack_status = Operation.SUCCESS_STATUS_MAP.get(op.operation_type)
            if new_stack_status:
                Stack.objects.filter(pk=op.stack_id).update(status=new_stack_status)
        elif status == 'FAILED':
            Stack.objects.filter(pk=op.stack_id).update(
                status='Error',
                error_message=error_message[:500] if error_message else '',
            )

    return {
        "operation_id": str(op.id),
        "status": op.status,
        "completed_at": now.isoformat(),
    }


def get_stack_operations(stack_id: str, limit: int = 20) -> list[dict]:
    """Return recent operations for a stack."""
    try:
        Stack.objects.get(pk=stack_id)
    except Stack.DoesNotExist:
        raise NotFoundError("Stack not found.")

    ops = Operation.objects.filter(stack_id=stack_id)[:limit]
    return [
        {
            "id": str(op.id),
            "operation_type": op.operation_type,
            "status": op.status,
            "error_message": op.error_message,
            "started_at": op.started_at.isoformat() if op.started_at else None,
            "completed_at": op.completed_at.isoformat() if op.completed_at else None,
            "created_at": op.created_at.isoformat(),
        }
        for op in ops
    ]


def timeout_stale_operations() -> int:
    """Mark RUNNING operations past their lease as TIMED_OUT.

    Called periodically (e.g. by crontainer) to recover stuck stacks.
    Returns the number of operations timed out.
    """
    now = timezone.now()
    stale_ops = Operation.objects.filter(
        status='RUNNING',
        lease_expires_at__lt=now,
    )
    count = 0
    for op in stale_ops:
        with transaction.atomic():
            locked_op = Operation.objects.select_for_update().get(pk=op.pk)
            if locked_op.status == 'RUNNING' and locked_op.lease_expires_at and locked_op.lease_expires_at < now:
                locked_op.status = 'TIMED_OUT'
                locked_op.completed_at = now
                locked_op.error_message = 'Operation exceeded lease duration and was marked as timed out.'
                locked_op.save()
                Stack.objects.filter(pk=locked_op.stack_id).update(
                    status='Error',
                    error_message='IaC operation timed out.',
                )
                count += 1
                logger.warning("Timed out stale operation %s for stack %s", op.pk, op.stack_id)

    return count
