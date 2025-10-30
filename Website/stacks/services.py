import logging
import json
import re
import requests
from django.http import JsonResponse
from django.db import transaction
from stacks.models import (
    Stack,
    PurchasableStack,
    StackIACAttribute,
)
from django.conf import settings
from projects.models import Project
from accounts.models import UserProfile
import os

import json
from django.http import JsonResponse, HttpRequest
from django.conf import settings
import uuid
import datetime

try:
    # azure-storage-blob is in requirements.txt; import here so module import error surfaces at runtime
    from azure.storage.blob import BlobServiceClient
except Exception:
    BlobServiceClient = None

from stacks.models import Stack, PurchasableStack
from projects.models import Project
from stacks.stack_managers import get_stack_manager

logger = logging.getLogger(__name__)    

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

        stack_manager = get_stack_manager(stack)

        for key, value in stack_manager.get_starter_stack_iac_attributes().items():
            StackIACAttribute.objects.create(
                stack_id=stack.id,
                attribute_name=key,
                attribute_value=value,
            )

        # try:
        send_to_azure_function("iac.create", {
            "stack_id": str(stack.id),
            "project_id": str(project.id),
            "org_id": str(project.organization.id),
            "iac": get_iac_attribute_dict_as_json(stack),
        })
        # except Exception as e:
        #     logger.warning(f"Failed to send message to Azure Function: {str(e)}")

    return stack

def update_stack(**kwargs) -> Stack:
    stack_id = kwargs.get("stack_id")
    source_code_path = kwargs.get("source_code_path", "")

    with transaction.atomic():

        stack = Stack.objects.get(pk=stack_id)
        stack_iac = get_iac_attribute_dict_as_json(stack)

        try:
            send_to_azure_function("iac.update", {
                "stack_id": str(stack.id),
                "source_code_path": str(source_code_path),
                "iac": stack_iac,
            })
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

        send_to_azure_function("iac.delete",
            {
                "stack_id": stack.id
            }
        )

        return True
    except Exception as e:
        logger.error(f"Failed to delete stack {stack.id}: {str(e)}")
        return False
    
def set_is_persistent_stack(stack: Stack, is_persistent: bool) -> bool:
    try:
        stack_manager = get_stack_manager(stack)
        stack_manager.set_is_persistent(is_persistent)

        send_to_azure_function("iac.update", {
            "stack_id": str(stack.id),
            "iac": get_iac_attribute_dict_as_json(stack),
        })

        return True
    except Exception as e:
        logger.error(f"Failed to set persistent for stack {stack.id}: {str(e)}")
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

        stack_manager = get_stack_manager(stack)
        stack_manager.set_source_code_upload()

        update_stack(stack_id=stack_id, source_code_path=blob_name)

        return JsonResponse({"success": True, "blob_name": blob_name, "blob_url": blob_client.url}, status=200)

    except Exception as e:
        # Log server-side for diagnostics and return minimal error to client
        print(f"Failed uploading source zip to Azure: {str(e)}")
        return JsonResponse({"error": f"Failed to upload file: {str(e)}"}, status=500)

def get_iac_attribute_dict_as_json(stack: Stack) -> dict:
    """Convert StackIACAttribute entries for the given stack into nested JSON structure."""
    attribute_dict = {}
    for attr in StackIACAttribute.objects.filter(stack=stack).all():
        attribute_dict[attr.attribute_name] = attr.attribute_value

    logger.warning(f"IAC Attribute Dict for Stack {stack.id}: {json.dumps(attribute_dict, indent=2)}")

    def parse_value(value):
        """Convert string representations to their actual types."""
        if not isinstance(value, str):
            return value
        
        # Strip whitespace
        value = value.strip()
        
        # Empty dictionary
        if value == "{}":
            return {}
        
        # Empty list
        if value == "[]":
            return []
        
        # Try to parse as decimal number (int or float)
        try:
            # Check if it's a number (including decimals)
            if re.match(r'^-?\d+(\.\d+)?$', value):
                if '.' in value:
                    return float(value)
                else:
                    return int(value)
        except ValueError:
            pass
        
        # Return original string if no conversion applies
        return value

    def ensure_list(container, key):
        if key not in container or not isinstance(container[key], list):
            container[key] = []
        return container[key]

    def ensure_dict(container, key):
        if key not in container or not isinstance(container[key], dict):
            container[key] = {}
        return container[key]

    index_re = re.compile(r"^(?P<name>[^\[\]]+)(?:\[(?P<idx>\d+)\])?$")

    def parse_segment(segment):
        # ("container[0]") -> ("container", 0, None, None)
        # ("value?name=FOO") -> ("value", None, "name", "FOO")
        # ("env") -> ("env", None, None, None)
        if "?" in segment:
            base, query = segment.split("?", 1)
            if "=" in query:
                qk, qv = query.split("=", 1)
            else:
                qk, qv = query, None
        else:
            base, qk, qv = segment, None, None

        m = index_re.match(base)
        if not m:
            return base, None, qk, qv
        name = m.group("name")
        idx = m.group("idx")
        return name, (int(idx) if idx is not None else None), qk, qv

    iac_json = {}

    for full_key, value in attribute_dict.items():
        parts = full_key.split(".")
        current = iac_json
        parent = None
        parent_key = None

        # Traverse all but last segment
        for i, seg in enumerate(parts[:-1]):
            name, idx, _, _ = parse_segment(seg)
            next_is_query_leaf = "?" in parts[i+1] and (i+1) == len(parts) - 1

            if idx is None:
                if next_is_query_leaf:
                    # parent[name] should be a list; we’ll append at the leaf
                    current_list = ensure_list(current, name)
                    parent = current
                    parent_key = name
                    current = current_list
                else:
                    current = ensure_dict(current, name)
            else:
                arr = ensure_list(current, name)
                while len(arr) <= idx:
                    arr.append({})
                current = arr[idx]

        # Handle the final segment
        last_seg = parts[-1]
        name, idx, qk, qv = parse_segment(last_seg)

        if qk is not None:
            # e.g. "...env.value?name=FOO": append {"name": qv, "value": value} to parent[parent_key]
            target_list = current if (parent is None or parent_key is None) else ensure_list(parent, parent_key)
            target_list.append({qk: qv, name: parse_value(value)})
        else:
            if idx is None:
                if isinstance(current, list):
                    current.append({name: parse_value(value)})
                else:
                    current[name] = parse_value(value)
            else:
                arr = ensure_list(current, name)
                while len(arr) <= idx:
                    arr.append(None)
                arr[idx] = parse_value(value)

    return iac_json


def send_to_azure_function(request_type: str, message_data: dict) -> bool:
    """
    Sends a message to Azure Function via HTTP trigger.
    """
    
    function_url = os.environ.get('AZURE_FUNCTION_URL')

    if not function_url:
        logger.error("Azure Function URL is not configured.")
        return False
    
    data = {
        "request_type": request_type,
        "data": message_data
    }

    try:
        # Send HTTP POST request to Azure Function
        print("Sending data to Azure Function:", function_url, data)
        response = requests.post(
            function_url,
            json=data,
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