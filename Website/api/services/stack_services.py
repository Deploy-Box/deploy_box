import logging
import json

from google.cloud import storage  # type: ignore
from google.oauth2 import service_account  # type: ignore
from django.http import HttpRequest, JsonResponse, FileResponse  # type: ignore
from django.shortcuts import get_object_or_404  # type: ignore
from django.conf import settings  # type: ignore
from django.db.models import F  # type: ignore
from django.db import transaction  # type: ignore

from api.utils import gcp_utils
from api.utils import MongoDBUtils
from accounts.models import Project, ProjectMember
from api.models import StackDatabase, StackBackend, Stack, StackFrontend, AvailableStack
from api.serializers.stacks_serializer import StackSerializer, StackDatabaseSerializer
from core.decorators import oauth_required, AuthHttpRequest
from core.helpers import assertRequiredFields
from accounts.services import get_project

logger = logging.getLogger(__name__)


def get_stacks(request: HttpRequest, stack_id: str | None = None) -> JsonResponse:
    user = request.user

    project = Project.objects.get(user=user)

    if stack_id:
        try:
            stack = Stack.objects.get(id=stack_id, project=project)
            stack = StackSerializer(stack).data
            return JsonResponse({"data": stack}, status=200)
        except Stack.DoesNotExist:
            return JsonResponse({"error": "Stack not found."}, status=404)
    else:
        stacks = Stack.objects.filter(project=project)
        stacks = StackSerializer(stacks, many=True).data
        return JsonResponse({"data": stacks}, status=200)


# TODO change to get all database stacks
def get_all_stacks(_: HttpRequest) -> JsonResponse:
    stacks = StackDatabase.objects.all()
    stacks = StackDatabaseSerializer(stacks, many=True).data
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
        return JsonResponse({"data": stacks_dict}, status=200)
    else:
        return JsonResponse({"error": "No stacks found."}, status=404)


def get_stack(
    request: HttpRequest, organization_id: str, project_id: str, stack_id: str
) -> JsonResponse:
    user = request.user
    project = get_project(user, organization_id, project_id)

    try:
        stack = Stack.objects.get(id=stack_id, project=project)
    except Stack.DoesNotExist:
        return JsonResponse({"error": "Stack not found."}, status=404)

    if stack is None:
        return JsonResponse({"error": "Stack not found."}, status=404)

    stack = StackSerializer(stack).data

    return JsonResponse({"data": stack}, status=200)


def add_stack(request: AuthHttpRequest) -> JsonResponse:
    user = request.auth_user

    response = assertRequiredFields(
        request, ["project_id", "available_stack_id", "name"]
    )

    if isinstance(response, JsonResponse):
        return response

    project_id, available_stack_id, name = response

    project_member = get_object_or_404(ProjectMember, user=user, project_id=project_id)

    if project_member.role not in ["owner", "admin"]:
        return JsonResponse(
            {"error": "User does not have permission to add a stack."}, status=403
        )

    project = get_object_or_404(Project, id=project_id)
    available_stack = get_object_or_404(AvailableStack, id=available_stack_id)

    try:
        with transaction.atomic():
            # Create the stack within a transaction
            stack = Stack.objects.create(
                name=name, project=project, purchased_stack=available_stack
            )

            # Deploy the stack - if this fails, the transaction will be rolled back
            if available_stack.type == "MERN":
                return deploy_MERN_stack(stack)
            else:
                return JsonResponse({"error": "Stack type not supported."}, status=400)
    except Exception as e:
        logger.error(f"Failed to create and deploy stack: {str(e)}")
        return JsonResponse(
            {"error": f"Failed to create and deploy stack: {str(e)}"}, status=500
        )


def deploy_MERN_stack(stack: Stack) -> JsonResponse:
    """
    Deploys a MERN stack by creating the necessary backend and frontend services.
    If any part of the deployment fails, the transaction will be rolled back.
    """
    try:
        stack_id = stack.id

        # Create deployment database
        mongodb_utils = MongoDBUtils()
        mongo_db_uri = mongodb_utils.deploy_mongodb_database(stack_id)
        stack_database = StackDatabase.objects.create(
            stack=stack,
            uri=mongo_db_uri,
        )

        backend_image = "gcr.io/deploy-box/mern-backend"
        print(f"Deploying backend with image: {backend_image}")
        backend_url = gcp_utils.deploy_service(
            f"backend-{stack_id}", backend_image, {"MONGO_URI": mongo_db_uri}
        )

        stack_backend = StackBackend.objects.create(
            stack=stack,
            url=backend_url,
            image_url=backend_image,
        )

        frontend_image = "gcr.io/deploy-box/mern-frontend"
        frontend_url = gcp_utils.deploy_service(
            f"frontend-{stack_id}",
            frontend_image,
            {"REACT_APP_BACKEND_URL": backend_url},
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
    except Exception as e:
        # Log the error and re-raise to trigger transaction rollback
        logger.error(f"Error deploying MERN stack: {str(e)}")
        raise


def deploy_stack(request: HttpRequest, stack_id: str | None) -> JsonResponse:
    if not stack_id:
        return JsonResponse({"error": "Stack ID is required."}, status=400)

    user = request.user
    project = Project.objects.get(user=user)

    # Get the stack object or return 404 if not found
    stack = get_object_or_404(Stack, id=stack_id, project=project)

    if stack.purchased_stack.variant == "MERN":
        return deploy_MERN_stack(stack, stack_id)
    else:
        # Handle other stack types if needed
        # For now, just return an error for unsupported stack types
        return JsonResponse(
            {
                "error": f"Deployment for stack type '{stack.purchased_stack.type}' with variant '{stack.purchased_stack.variant}' is not supported."
            },
            status=400,
        )


def update_stack(request: HttpRequest, stack_id: str | None) -> JsonResponse:
    if not stack_id:
        return JsonResponse({"error": "Stack ID is required."}, status=400)

    user = request.user
    project = Project.objects.get(user=user)

    stack = get_object_or_404(Stack, id=stack_id, project=project)
    if not stack:
        return JsonResponse({"error": "Stack not found."}, status=404)

    stack_type = request.GET.get("type", stack.purchased_stack.type)
    variant = request.GET.get("variant", stack.purchased_stack.variant)
    version = request.GET.get("version", stack.purchased_stack.version)

    stack.purchased_stack.type = stack_type
    stack.purchased_stack.variant = variant
    stack.purchased_stack.version = version
    stack.save()

    return JsonResponse(
        {
            "message": "Stack updated successfully.",
            "data": {
                "id": stack_id,
                "type": stack_type,
                "variant": variant,
                "version": version,
            },
        },
        status=200,
    )


def download_stack(
    request: HttpRequest, stack_id: str | None = None
) -> JsonResponse | FileResponse:
    if not stack_id:
        return JsonResponse({"error": "Stack ID is required."}, status=400)

    # Get the user's stack or return 404
    user = request.user
    project = get_project(user)

    stack = get_object_or_404(Stack, id=stack_id, project=project)

    # Load service account credentials
    credentials_path = settings.GCP.KEY_PATH

    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        client = storage.Client(credentials=credentials)
    except Exception as e:
        logger.error(f"Failed to initialize Google Cloud Storage client: {e}")
        return JsonResponse(
            {"error": "Failed to initialize Google Cloud Storage client."}, status=500
        )

    bucket_name = "deploy_box_bucket"
    blob_name = f"{stack.purchased_stack.type.upper()}.tar"

    try:
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # Ensure the file exists before attempting to download
        if not blob.exists(client):
            return JsonResponse(
                {
                    "error": f"Stack file '{blob_name}' not found in bucket '{bucket_name}'."
                },
                status=404,
            )

        # Stream the file response instead of loading everything into memory
        response = FileResponse(blob.open("rb"), content_type="application/x-tar")
        response["Content-Disposition"] = f'attachment; filename="{blob_name}"'
        return response

    except Exception as e:
        logger.error(f"Error downloading stack {stack_id}: {e}")
        return JsonResponse(
            {"error": f"An error occurred while downloading the stack: {str(e)}"},
            status=500,
        )


def update_database_storage_billing(request: HttpRequest) -> JsonResponse:
    data = json.loads(request.body)

    print("data: ", data)

    for stack_id, usage in data.items():
        print(stack_id, usage)
        StackDatabase.objects.filter(stack_id=stack_id).update(
            current_usage=F("current_usage") + usage
        )

    return JsonResponse(
        {"message": "Database storage billing updated successfully.", "data": data},
        status=200,
    )


@oauth_required()
def get_database_current_use_from_db(request: HttpRequest) -> JsonResponse:
    stacks = StackDatabase.objects.all()
    stacks = StackDatabaseSerializer(stacks, many=True).data
    print(stacks)

    stacks_dict = {}
    for stack in stacks:
        usage = stack.get("current_usage")
        temp = stack.get("stack")
        user_temp = stack.get("stack").get("user")

        if temp == None:
            stack_id = "no stack"
        else:
            stack_id = temp.get("id")

        if user_temp == None:
            user_id = "no user"
        else:
            user_id = user_temp.get("id")

        stacks_dict[stack_id] = (user_id, usage)

    print("stack_dict: ", stacks_dict)

    if stacks is not None:
        return JsonResponse({"stacks": stacks_dict}, status=200)
    else:
        return JsonResponse({"error": "No stacks found."}, status=404)
