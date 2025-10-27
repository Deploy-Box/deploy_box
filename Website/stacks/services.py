import logging
import json
import requests
from django.http import JsonResponse
from django.db import transaction
from stacks.models import (
    Stack,
    PurchasableStack,
)
from django.conf import settings
from projects.models import Project
from accounts.models import UserProfile
import os
from django.views.decorators.csrf import csrf_exempt
from .service_helpers import ServiceHelper

import json
from django.http import JsonResponse, HttpRequest, HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet, ModelViewSet
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
import uuid
import datetime

try:
    # azure-storage-blob is in requirements.txt; import here so module import error surfaces at runtime
    from azure.storage.blob import BlobServiceClient
except Exception:
    BlobServiceClient = None

from core.decorators import oauth_required, AuthHttpRequest
from stacks.models import Stack, PurchasableStack
from stacks.serializers import (
    StackDatabaseSerializer,
    StackSerializer,
    StackCreateSerializer,
    StackUpdateSerializer,
    PurchasableStackCreateSerializer,
    StackDatabaseUpdateSerializer,
    StackIACOverwriteSerializer,
    StackStatusUpdateSerializer,
    StackIACUpdateSerializer,
    StackIACStateUpdateSerializer,
)
from projects.models import Project
import stacks.services as services
from django.shortcuts import get_object_or_404
from rest_framework import permissions, filters
from rest_framework import viewsets

logger = logging.getLogger(__name__)

def send_to_azure_function(message_data: dict, function_url: str | None = None) -> bool:
    """
    Sends a message to Azure Function via HTTP trigger.
    
    Args:
        message_data (dict): The data to send as a message
        function_url (str): The URL of the Azure Function HTTP trigger
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    function_url = function_url or os.environ.get('AZURE_FUNCTION_URL')

    if not function_url:
        logger.error("Azure Function URL is not configured.")
        return False

    try:
        # Send HTTP POST request to Azure Function
        response = requests.post(
            function_url,
            json=message_data,
            headers={'Content-Type': 'application/json'},
            timeout=30  # 30 second timeout
        )
        
        # Check if the request was successful
        if response.status_code in [200, 202]:
            logger.info(f"Successfully sent message to Azure Function: {function_url}")
            return True
        else:
            logger.error(f"Azure Function returned status code {response.status_code}: {response.text}")
            return False
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send message to Azure Function: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending message to Azure Function: {str(e)}")
        return False
    

def add_stack(**kwargs) -> Stack:
    name = kwargs.get("name")
    project_id = kwargs.get("project_id")
    purchasable_stack_id = kwargs.get("purchasable_stack_id")

    project = Project.objects.get(pk=project_id)
    purchasable_stack = PurchasableStack.objects.get(pk=purchasable_stack_id)

    with transaction.atomic():

        print(f"Variant: {purchasable_stack.variant}")

        stack = Stack.objects.create(
            name=name, project=project, purchased_stack=purchasable_stack, status="PROVISIONING"
        )

        

        # Put request on Azure Service Bus
        message_data = {
            "request_type": "iac.create",
            "source": os.environ.get("HOST"),          
            "data": {
                "stack_id": str(stack.id),
                "project_id": str(project.id),
                "org_id": str(project.organization.id),
                "purchasable_stack_type": purchasable_stack.type.upper(),
                "purchasable_stack_variant": purchasable_stack.variant.upper(),
                "purchasable_stack_version": purchasable_stack.version,
            }
        }

        # Send message to Azure Function (non-blocking)
        try:
            send_to_azure_function(message_data)
        except Exception as e:
            logger.warning(f"Failed to send message to Azure Function: {str(e)}")

    return stack

# project = Project.objects.all()[0]
# purchasable_stack = PurchasableStack.objects.all()[0]
# add_stack(name="test", project_id=project.id, purchasable_stack_id=purchasable_stack.id)


def update_stack(**kwargs) -> Stack:
    stack_id = kwargs.get("stack_id")
    stack_iac = kwargs.get("stack_iac", {})
    source_code_path = kwargs.get("source_code_path", "")


    with transaction.atomic():

        stack = Stack.objects.get(pk=stack_id)

        if not stack_iac:
            stack_iac = stack.iac

        # Put request on Azure Service Bus
        message_data = {
            "request_type": "iac.update",
            "source": os.environ.get("HOST"),
            "data": {
                "stack_id": str(stack.id),
                "source_code_path": str(source_code_path),
                "iac": stack_iac,
            }
        }

        # Send message to Azure Function (non-blocking)
        try:
            send_to_azure_function(message_data)
        except Exception as e:
            logger.warning(f"Failed to send message to Azure Function: {str(e)}")

    return stack


def get_stacks(user: UserProfile) -> list[Stack]:
    projects = Project.objects.filter(projectmember__user=user)

    return list(Stack.objects.filter(project__in=projects).order_by("-created_at"))


def post_purchasable_stack(
    type: str, variant: str, version: str, price_id: str
) -> JsonResponse:
    try:
        with transaction.atomic():
            PurchasableStack.objects.create(
                type=type, variant=variant, version=version, price_id=price_id
            )
            return JsonResponse(
                {"message": "Purchasable stack created successfully."}, status=201
            )
    except Exception as e:
        logger.error(f"Failed to create purchasable stack: {str(e)}")
        return JsonResponse(
            {"error": f"Failed to create purchasable stack: {str(e)}"}, status=500
        )

def delete_stack(stack: Stack) -> bool:
    try:
        stack.status = "DELETING"
        stack.save()

        print(f"Deleting stack {stack.id}...")
        send_to_azure_function(
            {
                "request_type": "iac.delete",
                "source": os.environ.get("HOST"),
                "data": {
                    "stack_id": stack.id,
                    "iac": stack.iac
                }
            }
        )
        return True
    except Exception as e:
        logger.error(f"Failed to delete stack {stack.id}: {str(e)}")
        return False
    
def upload_source_code(request: HttpRequest, stack_id: str) -> JsonResponse:
    """Accept a multipart/form-data POST with a file field named 'source_zip' and upload it to Azure Blob Storage.

    Expects Azure configuration in Django settings under `AZURE.STORAGE_CONNECTION_STRING` and
    `AZURE.CONTAINER_NAME` (or environment variables `AZURE_STORAGE_CONNECTION_STRING` and `CONTAINER_NAME`).
    Returns JSON with the uploaded blob URL on success.
    """
    # Only allow POST
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Ensure file present
    if "source_zip" not in request.FILES:
        return JsonResponse({"error": "No file uploaded under 'source_zip'."}, status=400)

    uploaded_file = request.FILES["source_zip"]

    # Verify Azure Blob client available
    if BlobServiceClient is None:
        return JsonResponse({"error": "Azure Blob Storage client not available (missing package)."}, status=500)

    # Read Azure configuration from settings
    azure_cfg = getattr(settings, 'AZURE', {}) if hasattr(settings, 'AZURE') else {}
    print(azure_cfg)
    conn_str = azure_cfg.get('STORAGE_CONNECTION_STRING') or getattr(settings, 'AZURE_STORAGE_CONNECTION_STRING', None)
    container = azure_cfg.get('CONTAINER_NAME') or getattr(settings, 'CONTAINER_NAME', None)

    if not conn_str or not container:
        return JsonResponse({"error": "Azure storage configuration missing. Set AZURE_STORAGE_CONNECTION_STRING and CONTAINER_NAME."}, status=500)

    try:
        # Create client and upload
        blob_service_client = BlobServiceClient.from_connection_string(conn_str)
        container_client = blob_service_client.get_container_client(container)

        # Build a unique blob name preserving stack context
        ts = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
        unique = uuid.uuid4().hex
        blob_name = f"{stack_id}/source-{ts}-{unique}.zip"

        blob_client = container_client.get_blob_client(blob_name)

        # streamed upload from the uploaded file file-like object
        file_stream = uploaded_file.file if hasattr(uploaded_file, 'file') else uploaded_file

        # upload_blob accepts a file-like object or bytes
        blob_client.upload_blob(file_stream, overwrite=True)

        stack = Stack.objects.get(id=stack_id)

        print("Current IAC:", stack.iac)

        stack_iac = stack.iac

        # TODO: This will only work for Django Stacks, still need to figure out how this will work in general

        del stack_iac["azurerm_container_app"]["azurerm_container_app-1"]["template"]["container"][0]["image"]
        stack_iac["azurerm_container_app"]["azurerm_container_app-1"]["template"]["container"][0].update({"build_context": "source_code"})

        services.update_stack(stack_id=stack_id, source_code_path=blob_name, stack_iac=stack_iac)

        return JsonResponse({"success": True, "blob_name": blob_name, "blob_url": blob_client.url}, status=200)

    except Exception as e:
        # Log server-side for diagnostics and return minimal error to client
        print(f"Failed uploading source zip to Azure: {str(e)}")
        return JsonResponse({"error": f"Failed to upload file: {str(e)}"}, status=500)
