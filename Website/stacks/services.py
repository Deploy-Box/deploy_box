import logging
import secrets
import json
from django.http import JsonResponse
from django.db import transaction
from requests import request
import requests
from stacks.models import (
    Stack,
    PurchasableStack,
    StackDatabase,
    StackBackend,
    StackFrontend,
    StackGoogleCloudRun,
)
from projects.models import Project
from core.utils import GCPUtils, MongoDBUtils
from accounts.models import User
from .forms import EnvFileUploadForm
from dotenv import dotenv_values
import os

logger = logging.getLogger(__name__)


def add_stack(
    project: Project, purchasable_stack: PurchasableStack, name: str
) -> JsonResponse:
    try:
        with transaction.atomic():
            stack = Stack.objects.create(
                name=name, project=project, purchased_stack=purchasable_stack
            )

            if purchasable_stack.type == "MERN":
                return deploy_MERN_stack(stack)
            elif purchasable_stack.type == "Django":
                return deploy_django_stack(stack)
            else:
                return JsonResponse({"error": "Stack type not supported."}, status=400)

    except Exception as e:
        logger.error(f"Failed to create and deploy stack: {str(e)}")
        return JsonResponse(
            {"error": f"Failed to create and deploy stack: {str(e)}"}, status=500
        )


def get_stack(**kwargs):
    print(f"Getting stack: {kwargs}")
    stack = Stack.objects.get(pk=kwargs.get("pk"))
    stack_google_cloud_run = StackGoogleCloudRun.objects.filter(stack=stack).first()
    if stack_google_cloud_run:
        gcp_utils = GCPUtils()
        build_status = gcp_utils.get_build_status(
            stack_google_cloud_run.build_status_url
        )
        print(f"Build status: {build_status}")
        stack_google_cloud_run.state = build_status
        stack_google_cloud_run.save()
    return Stack.objects.filter(pk=stack.id)


def update_stack(stack: Stack, root_directory: str | None = None) -> bool:
    if root_directory:
        stack.root_directory = root_directory
    stack.save()
    return True


def delete_stack(stack: Stack) -> bool:
    try:
        stack.delete()
    except Exception as e:
        logger.error(f"Failed to delete stack: {str(e)}")
        return False

    return True


def get_stacks(user: User) -> list[Stack]:
    projects = Project.objects.filter(projectmember__user=user)

    return list(Stack.objects.filter(project__in=projects).order_by("-created_at"))


def deploy_MERN_stack(stack: Stack) -> JsonResponse:
    """
    Deploys a MERN stack by creating the necessary backend and frontend services.
    If any part of the deployment fails, the transaction will be rolled back.
    """
    gcp_utils = GCPUtils()
    mongodb_utils = MongoDBUtils()

    stack_id = stack.id

    # Create deployment database
    mongo_db_uri = mongodb_utils.deploy_mongodb_database(stack_id)
    stack_database = StackDatabase.objects.create(
        stack=stack,
        uri=mongo_db_uri,
    )

    backend_image = f"gcr.io/{gcp_utils.project_id}/mern-backend"
    print(f"Deploying backend with image: {backend_image}")
    backend_url = gcp_utils.deploy_service(
        stack_id, backend_image, "backend", {"MONGO_URI": mongo_db_uri}, port=5000
    )

    stack_backend = StackBackend.objects.create(
        stack=stack,
        url=backend_url,
        image_url=backend_image,
    )

    frontend_image = f"gcr.io/{gcp_utils.project_id}/mern-frontend"
    print(f"Deploying frontend with image: {frontend_image}")
    frontend_url = gcp_utils.deploy_service(
        stack_id,
        frontend_image,
        "frontend",
        {"REACT_APP_BACKEND_URL": backend_url},
        port=8080,
    )

    stack_frontend = StackFrontend.objects.create(
        stack=stack,
        url=frontend_url,
        image_url=frontend_image,
    )

    stack_database.save()
    stack_backend.save()
    stack_frontend.save()

    # Return the response with the deployed URLs
    return JsonResponse(
        {
            "message": "MERN stack deployed successfully.",
            "data": {
                "stack_id": stack_id,
                "mongo_db_uri": mongo_db_uri,
                "backend_url": backend_url,
                "frontend_url": frontend_url,
            },
        },
        status=201,
    )


def deploy_django_stack(stack: Stack):
    gcp_utils = GCPUtils()

    stack_id = stack.id

    django_secret_key = secrets.token_urlsafe(50)

    backend_image = f"gcr.io/{gcp_utils.project_id}/django"
    print(f"Deploying backend with image: {backend_image}")
    response = gcp_utils.deploy_service(
        stack_id,
        backend_image,
        "django",
        {"DJANGO_SECRET_KEY": django_secret_key},
        port=8000,
    )

    stack_google_cloud_run = StackGoogleCloudRun.objects.create(
        stack=stack,
        image_url=backend_image,
        build_status_url=response.get("build_status_url", ""),
    )

    stack_google_cloud_run.save()

    return JsonResponse(
        {
            "message": "Django stack deployed successfully.",
            "data": {
                "stack_id": stack_id,
                "build_status_url": response.get("build_status_url", ""),
            },
        },
        status=201,
    )


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


def get_all_stack_databases() -> list[StackDatabase]:
    return list(StackDatabase.objects.all())


# TODO: show loading indicator
def post_stack_env(
    stack_id: str, selected_frameworks, selected_locations, uploaded_file
):

    env_file = uploaded_file

    if selected_locations == "none":

        total_stack_id = selected_frameworks + "-" + stack_id

    else:
        total_stack_id = selected_frameworks + "-" + selected_locations + "-" + stack_id

    # Save the file temporarily
    with open("temp.env", "wb") as f:
        for chunk in env_file.chunks():
            f.write(chunk)

    # Parse the .env file into a dictionary
    env_dict = dotenv_values("temp.env")

    Cloud = GCPUtils()

    Cloud.put_service_envs(total_stack_id, env_dict)

    # Clean up temporary file
    os.remove("temp.env")

    # You can now use the env_dict to update your Google Cloud build instance or whatever you need
    return JsonResponse({"status": "success"})


def update_stack_databases_usages(data) -> bool:
    """
    Updates the usage of multiple stack databases.

    Args:
        data (dict): Dictionary containing the data with stack database updates

    Returns:
        bool: True if all updates were successful
    """
    print("Data: ", data)
    print(type(data))
    try:
        data = json.loads(data)
        print("Data: ")
        print("Data: ", data.get("data"))
        print(type(data.get("data")))
        data = json.loads(data.get("data"))
        print("Data: ", data)
        for stack_database_id, usage in data.items():
            stack_database = StackDatabase.objects.get(pk=stack_database_id)
            stack_database.current_usage = usage
            stack_database.save()
        return True
    except Exception as e:
        logger.error(f"Failed to update stack databases usages: {str(e)}")
        return False
