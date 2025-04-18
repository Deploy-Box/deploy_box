import logging
from django.http import JsonResponse
from django.db import transaction

from stacks.models import (
    Stack,
    PurchasableStack,
    StackDatabase,
    StackBackend,
    StackFrontend,
)
from projects.models import Project
from core.utils import GCPUtils, MongoDBUtils
from accounts.models import User

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
            else:
                return JsonResponse({"error": "Stack type not supported."}, status=400)
    except Exception as e:
        logger.error(f"Failed to create and deploy stack: {str(e)}")
        return JsonResponse(
            {"error": f"Failed to create and deploy stack: {str(e)}"}, status=500
        )


def get_stack(request) -> JsonResponse:
    return JsonResponse({"message": "Stack retrieved successfully."})

def get_stacks(user: User) -> list[Stack]:
    return list(Stack.objects.filter(project__user=user).order_by("-created_at"))


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

    backend_image = "gcr.io/deploy-box/mern-backend"
    print(f"Deploying backend with image: {backend_image}")
    backend_url = gcp_utils.post_build_and_deploy(
        f"backend-{stack_id}", backend_image, {"MONGO_URI": mongo_db_uri}, "backend"
    )

    stack_backend = StackBackend.objects.create(
        stack=stack,
        url=backend_url,
        image_url=backend_image,
    )

    frontend_image = "gcr.io/deploy-box/mern-frontend"
    frontend_url = gcp_utils.post_build_and_deploy(
        f"frontend-{stack_id}",
        frontend_image,
        {"REACT_APP_BACKEND_URL": backend_url},
        "frontend",
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
