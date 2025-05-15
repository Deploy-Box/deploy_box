from django.http import JsonResponse, HttpRequest, HttpResponse

from core.decorators import oauth_required, AuthHttpRequest
import stacks.handlers as handlers
from core.utils.gcp.main import GCPUtils


@oauth_required()
def base_routing(
    request: AuthHttpRequest,
) -> JsonResponse:
    # GET: Fetch available stacks or a specific stack
    print(request.method)
    if request.method == "GET":
        return handlers.get_stack(request)

    # POST: Add a new stack
    elif request.method == "POST":
        return handlers.post_stack(request)

    # If the request method is not handled, return a 405 Method Not Allowed
    return JsonResponse({"error": "Method not allowed."}, status=405)


@oauth_required()
def specific_routing(
    request: AuthHttpRequest,
    stack_id: str,
) -> JsonResponse:
    # GET: Fetch a specific stack
    if request.method == "GET":
        return handlers.get_stack(request)

    # POST: Update a specific stack
    elif request.method == "POST":
        return handlers.post_stack(request)

    # DELETE: Delete a specific stack
    elif request.method == "DELETE":
        return handlers.delete_stack(request, stack_id)

    # UPDATE: Update a specific stack
    elif request.method == "PATCH":
        return handlers.patch_stack(request, stack_id)

    # If the request method is not handled, return a 405 Method Not Allowed
    return JsonResponse({"error": "Method not allowed."}, status=405)


@oauth_required()
def purchasable_stack_routing(
    request: AuthHttpRequest,
) -> JsonResponse:
    # GET: Fetch available stacks or a specific stack
    if request.method == "GET":
        return handlers.get_purchasable_stack(request)

    # POST: Add a new purchasable stack
    elif request.method == "POST":
        return handlers.post_purchasable_stack(request)

    # If the request method is not handled, return a 405 Method Not Allowed
    return JsonResponse({"error": "Method not allowed."}, status=405)


# @oauth_required()
def stack_env_routing(
    request: AuthHttpRequest,
    stack_id: str,
) -> JsonResponse:
    print(request.FILES)
    # GET: Fetch environment variables for a specific stack
    if request.method == "GET":
        return handlers.get_stack_env(request, stack_id)

    # POST: Update environment variables for a specific stack
    elif request.method == "POST":
        return handlers.post_stack_env(request, stack_id)

    # DELETE: Delete environment variables for a specific stack
    elif request.method == "DELETE":
        return handlers.delete_stack_env(request, stack_id)

    # If the request method is not handled, return a 405 Method Not Allowed
    return JsonResponse({"error": "Method not allowed."}, status=405)


import google.cloud.storage as storage
import google.api_core.exceptions as exceptions
from stacks.models import Stack
import requests


def download_stack(request: HttpRequest, stack_id: str):
    # Get the bucket name and file name from the request
    bucket_name = "deploy-box-prod-source-code"
    file_name = f"{stack_id}/source.zip"  # Adding trailing slash to indicate folder

    if not bucket_name or not file_name:
        return JsonResponse(
            {"error": "Bucket name and file name are required"}, status=400
        )

    try:
        # Initialize GCP storage client
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)

        # Download the file content
        file_content = blob.download_as_bytes()

        # Create the response with file download headers
        response = HttpResponse(file_content, content_type="application/octet-stream")
        response["Content-Disposition"] = (
            f'attachment; filename="{file_name.split("/")[-1]}"'
        )
        return response

    except exceptions.NotFound:
        stack = Stack.objects.get(id=stack_id)
        print("Checking Github")

        if not stack:
            return JsonResponse({"error": "Stack not found"}, status=404)

        url = f"https://raw.githubusercontent.com/Deploy-Box/{stack.purchased_stack.type}/main/source.zip"

        response = requests.get(url)
        response.raise_for_status()

        # Create the response with file download headers
        response = HttpResponse(
            response.content, content_type="application/octet-stream"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{file_name.split("/")[-1]}"'
        )

        return response

    except Exception as e:
        return JsonResponse({"error": f"Failed to download file: {str(e)}"}, status=500)


def get_all_stack_databases(request: HttpRequest) -> JsonResponse:
    return handlers.get_all_stack_databases()


def update_stack_databases_usages(request: HttpRequest) -> JsonResponse:
    return handlers.update_stack_databases_usages(request)
