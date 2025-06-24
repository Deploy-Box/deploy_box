import logging
import secrets
import json
from django.http import JsonResponse
from django.db import transaction
from stacks.models import (
    Stack,
    PurchasableStack,
    StackDatabase,
    StackGoogleCloudRun,
)
from projects.models import Project
from core.utils import MongoDBUtils
from core.utils.DeployBoxIAC.main import AzureDeployBoxIAC
from accounts.models import UserProfile
from dotenv import dotenv_values
import os
from typing import Union
from stacks.MERN_IAC import get_MERN_IAC
from stacks.Django_IAC import get_Django_IAC
from core.utils.DeployBoxIAC.main import main, DeployBoxIAC

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
            name=name, project=project, purchased_stack=purchasable_stack
        )

        variant = purchasable_stack.variant.lower()

        if purchasable_stack.type == "MERN":
            deploy_MERN_stack(project, stack, variant)
        elif purchasable_stack.type == "DJANGO":
            deploy_django_stack(project, stack, variant)
        else:
            JsonResponse({"error": "Stack type not supported."}, status=400)

    return stack


def update_stack(stack: Stack, root_directory: Union[str, None] = None) -> bool:
    if root_directory:
        stack.root_directory = root_directory
    stack.save()
    return True


def delete_stack(stack: Stack) -> bool:
    try:
        print(f"Deleting stack: {stack.id}")
        resource_group_name = stack.id + "-rg"
        cloud = DeployBoxIAC()
        cloud.deploy(resource_group_name, {})
        # stack.delete()
    except Exception as e:
        logger.error(f"Failed to delete stack: {str(e)}")
        return False

    return True


def get_stacks(user: UserProfile) -> list[Stack]:
    projects = Project.objects.filter(projectmember__user=user)

    return list(Stack.objects.filter(project__in=projects).order_by("-created_at"))


def deploy_MERN_stack(project: Project, stack: Stack, variant: str):
    """
    Deploys a MERN stack by creating the necessary backend and frontend services.
    If any part of the deployment fails, the transaction will be rolled back.
    """
    # mongodb_utils = MongoDBUtils()

    stack_id = stack.id

    # Create deployment database
    # mongo_db_uri = mongodb_utils.deploy_mongodb_database(stack_id)

    resource_group_name, mern_iac = get_MERN_IAC(
        stack_id, project.id, project.organization.id
    )

    stack.iac = mern_iac

    main(resource_group_name, mern_iac)

    stack.save()

    # if variant == "premium" or variant == "pro":
    #     env_dict["JWT_SECRET"] = secrets.token_urlsafe(50)


def deploy_django_stack(project: Project, stack: Stack, variant: str):
    stack_id = stack.id

    django_secret_key = secrets.token_urlsafe(50)

    resource_group_name, django_iac = get_Django_IAC(
        stack_id, project.id, project.organization.id, django_secret_key
    )

    stack.iac = django_iac

    main(resource_group_name, django_iac)

    stack.save()


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
    """
    Uploads an env file and sets its values as secrets and environment variables
    in the corresponding Azure Container App using AzureDeployBoxIAC.
    """
    # Save the uploaded file temporarily
    with open("temp.env", "wb") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    # Parse the .env file into a dictionary
    env_dict = dotenv_values("temp.env")

    # Clean up temporary file
    os.remove("temp.env")

    # Determine resource group and app name
    if selected_locations == "none":
        app_name = f"{selected_frameworks}-{stack_id}"
    else:
        app_name = f"{selected_frameworks}-{selected_locations}-{stack_id}"

    resource_group_name = stack_id + "-rg"  # Or derive dynamically if needed

    stack = Stack.objects.get(id=stack_id)
    if not stack:
        return JsonResponse(
            {"status": "error", "message": "Stack not found."}, status=404
        )

    iac = stack.iac
    # Add secrets and environment variables to the Azure Container App
    cloud = AzureDeployBoxIAC()
    result = cloud.add_container_app_envs_as_secrets(
        iac, app_name, env_dict, "testing-mern"
    )

    if result is None:
        return JsonResponse(
            {"status": "error", "message": "Failed to update secrets."}, status=500
        )

    # Update the stack with the new IAC
    stack.iac = iac

    main(resource_group_name, iac)

    stack.save()

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
