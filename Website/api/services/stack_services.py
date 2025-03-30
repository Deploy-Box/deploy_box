from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from api.serializers.stacks_serializer import StacksSerializer, StackDatabasesSerializer
import requests
from django.http import FileResponse
from google.cloud import storage
import os
from google.oauth2 import service_account
from django.shortcuts import get_object_or_404
import logging
from django.conf import settings
import api.utils.gcp_utils as gcp_utils
import api.utils.mongodb_utils as mongodb_utils
from api.models import StackDatabases, StackBackends, Stacks, StackFrontends
from django.db.models import F


logger = logging.getLogger(__name__)


def get_stacks(request: Request, stack_id: str = None) -> Response:
    user = request.user

    if stack_id:
        try:
            stack = Stacks.objects.get(id=stack_id, user=user)
            stack = StacksSerializer(stack).data
            return Response({"data": stack}, status=status.HTTP_200_OK)
        except Stacks.DoesNotExist:

            return Response({"error": "Stack Not Found"}, status.HTTP_404_NOT_FOUND)
    else:
        stacks = Stacks.objects.filter(user=user)
        stacks = StacksSerializer(stacks, many=True).data
        return Response({"data": stacks}, status.HTTP_200_OK)
    
#TODO change to get all database stacks
def get_all_stacks(request: Request):
    stacks = StackDatabases.objects.all()
    stacks = StackDatabasesSerializer(stacks, many=True).data
    print(stacks)


    stacks_dict = {}
    for stack in stacks:
        uri = stack.get("uri")
        temp = stack.get("stack")

        if temp == None:
            stack_id = "no stack"
        else:
            stack_id = temp.get("id")

        if stack_id in stacks_dict:
            stacks_dict[stack_id].append(uri)
        else:
            stacks_dict[stack_id] = [uri]

    print("stack_dict: ", stacks_dict)

    if stacks is not None:
        return Response({"stacks": stacks_dict}, status.HTTP_200_OK)
    else:
        return Response("error in get all stacks", status.HTTP_400_BAD_REQUEST)


def add_stack(request: Request) -> Response:
    user = request.user
    stack_type = request.data.get("type")
    variant = request.data.get("variant")
    version = request.data.get("version")

    if not stack_type or not variant or not version:
        return Response(
            {"error": "Type, variant, and version are required."},
            status.HTTP_400_BAD_REQUEST,
        )

    if Stacks.objects.filter(
        user=user, type=stack_type, variant=variant, version=version
    ).exists():
        return Response({"error": "Stack already exists"}, status.HTTP_400_BAD_REQUEST)

    Stacks.objects.create(user=user, type=stack_type, variant=variant, version=version)
    return Response({"message": "Stack added successfully"}, status.HTTP_201_CREATED)


def deploy_stack(_, stack_id: str) -> Response:
    stack = get_object_or_404(Stacks, id=stack_id)

    # Create deployment database
    mongo_db_uri = mongodb_utils.deploy_mongodb_database(stack_id)
    stack_database = StackDatabases.objects.create(
        stack=stack,
        uri=mongo_db_uri,
    )

    # TODO: Use the backend image from the stack
    backend_image = "kalebwbishop/mern-backend"
    print(f"Deploying backend with image: {backend_image}")
    backend_url = gcp_utils.deploy_service(
        f"backend-{stack_id}", backend_image, {"MONGO_URI": mongo_db_uri}
    )

    stack_backend = StackBackends.objects.create(
        stack=stack,
        url=backend_url,
        image_url=backend_image,
    )

    # TODO: Use the frontend image from the stack
    frontend_image = "kalebwbishop/mern-frontend"
    frontend_url = gcp_utils.deploy_service(
        f"frontend-{stack_id}",
        frontend_image,
        {"REACT_APP_BACKEND_URL": backend_url},
    )

    stack_frontend = StackFrontends.objects.create(
        stack=stack,
        url=frontend_url,
        image_url=frontend_image,
    )

    return Response(
        {"message": "Stack deployed successfully"}, status=status.HTTP_200_OK
    )


def update_stack(request: Request, stack_id: str) -> Response:
    if not stack_id:
        return Response(
            {"error": "Stack ID is required."}, status=status.HTTP_400_BAD_REQUEST
        )

    stack = get_stacks(request, stack_id)
    if not stack:
        return Response({"error": "Stack not found."}, status=status.HTTP_404_NOT_FOUND)

    stack_type = request.data.get("type", stack.type)
    variant = request.data.get("variant", stack.variant)
    version = request.data.get("version", stack.version)

    stack.type = stack_type
    stack.variant = variant
    stack.version = version
    stack.save()

    return Response({"message": "Stack updated successfully"}, status.HTTP_200_OK)


def download_stack(request: Request, stack_id: str = None) -> Response:
    if not stack_id:
        return Response(
            {"error": "Stack ID is required."}, status=status.HTTP_400_BAD_REQUEST
        )

    # Get the user's stack or return 404
    stack = get_object_or_404(Stacks, id=stack_id, user=request.user)

    # Load service account credentials
    credentials_path = settings.GCP.KEY_PATH

    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        client = storage.Client(credentials=credentials)
    except Exception as e:
        logger.error(f"Failed to initialize Google Cloud Storage client: {e}")
        return Response(
            {"error": "Internal server error."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    bucket_name = "deploy_box_bucket"
    blob_name = f"{stack.stack.type.upper()}.tar"

    try:
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # Ensure the file exists before attempting to download
        if not blob.exists(client):
            return Response(
                {"error": "File not found in bucket"}, status=status.HTTP_404_NOT_FOUND
            )

        # Stream the file response instead of loading everything into memory
        response = FileResponse(blob.open("rb"), content_type="application/x-tar")
        response["Content-Disposition"] = f'attachment; filename="{blob_name}"'
        return response

    except Exception as e:
        logger.error(f"Error downloading stack {stack_id}: {e}")
        return Response(
            {"error": "Error downloading stack."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    

def update_database_storage_billing(request: Request):
    data = request.data

    for stack_id, usage in data.items():
        StackDatabases.objects.filter(stack_id=stack_id).update(current_usage=F('current_usage')+usage)



    return Response({"data": data}, status=status.HTTP_200_OK)

