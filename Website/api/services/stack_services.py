import logging
from django.http import HttpRequest, JsonResponse, FileResponse
from google.cloud import storage
from google.oauth2 import service_account
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.db.models import F

import api.utils.gcp_utils as gcp_utils
from api.utils import MongoDBUtils
from api.models import StackDatabases, StackBackends, Stacks, StackFrontends
from api.serializers.stacks_serializer import StacksSerializer, StackDatabasesSerializer

logger = logging.getLogger(__name__)

def get_stacks(request: HttpRequest, stack_id: str | None = None) -> JsonResponse:
    user = request.user

    if stack_id:
        try:
            stack = Stacks.objects.get(id=stack_id, user=user)
            stack = StacksSerializer(stack).data
            return JsonResponse({"data": stack}, status=200)
        except Stacks.DoesNotExist:

            return JsonResponse(
                {"error": "Stack not found."},
                status=404
            )
    else:
        stacks = Stacks.objects.filter(user=user)
        stacks = StacksSerializer(stacks, many=True).data
        return JsonResponse(
            {"data": stacks},
            status=200
        )
    
#TODO change to get all database stacks
def get_all_stacks(_: HttpRequest) -> JsonResponse:
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
        return JsonResponse(
            {"data": stacks_dict},
            status=200
        )
    else:
        return JsonResponse(
            {"error": "No stacks found."},
            status=404
        )


def add_stack(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        user = request.user
        stack_type = request.POST.get("type")
        variant = request.POST.get("variant")
        version = request.POST.get("version")

        if not stack_type or not variant or not version:
            return JsonResponse(
                {"error": "Type, variant, and version are required."},
                status=400
            )

        if Stacks.objects.filter(
            user=user, type=stack_type, variant=variant, version=version
        ).exists():
            return JsonResponse(
                {"error": "Stack with the same type, variant, and version already exists."},
                status=400
            )

        Stacks.objects.create(user=user, type=stack_type, variant=variant, version=version)
        return JsonResponse(
            {"message": "Stack added successfully."},
            status=201
        )
    
    return JsonResponse(
        {"error": "Invalid request method. Only POST is allowed."},
        status=405
    )   

def deploy_MERN_stack(stack: Stacks, stack_id: str) -> JsonResponse:
    """
    Deploys a MERN stack by creating the necessary backend and frontend services."
    """
    # Create deployment database
    mongodb_utils = MongoDBUtils()
    mongo_db_uri = mongodb_utils.deploy_mongodb_database(stack_id)
    stack_database = StackDatabases.objects.create(
        stack=stack,
        uri=mongo_db_uri,
    )

    backend_image = "gcr.io/deploy-box/mern-backend"
    print(f"Deploying backend with image: {backend_image}")
    backend_url = gcp_utils.deploy_service(
        f"backend-{stack_id}", backend_image, {"MONGO_URI": mongo_db_uri}
    )

    stack_backend = StackBackends.objects.create(
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

    stack_frontend = StackFrontends.objects.create(
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
                "frontend_url": frontend_url
            }
        },
        status=201
    )


def deploy_stack(request: HttpRequest, stack_id: str | None) -> JsonResponse:
    if not stack_id:
        return JsonResponse(
            {"error": "Stack ID is required."},
            status=400
        )
    
    # Get the stack object or return 404 if not found
    stack = get_object_or_404(Stacks, id=stack_id, user=request.user)

    if stack.purchased_stack.variant == "MERN":
        return deploy_MERN_stack(stack, stack_id)
    else:
        # Handle other stack types if needed
        # For now, just return an error for unsupported stack types
        return JsonResponse(
            {"error": f"Deployment for stack type '{stack.purchased_stack.type}' with variant '{stack.purchased_stack.variant}' is not supported."},
            status=400
        )
    

def update_stack(request: HttpRequest, stack_id: str | None) -> JsonResponse:
    if not stack_id:
        return JsonResponse(
            {"error": "Stack ID is required."},
            status=400
        )

    stack = get_stacks(request, stack_id)
    if not stack:
        return JsonResponse(
            {"error": "Stack not found."},
            status=404
        )

    stack_type = request.GET.get("type", stack.type)
    variant = request.GET.get("variant", stack.variant)
    version = request.GET.get("version", stack.version)

    stack.type = stack_type
    stack.variant = variant
    stack.version = version
    stack.save()

    return JsonResponse(
        {
            "message": "Stack updated successfully.",
            "data": {
                "id": stack_id,
                "type": stack_type,
                "variant": variant,
                "version": version
            }
        },
        status=200
    )


def download_stack(request: HttpRequest, stack_id: str | None = None) -> JsonResponse:
    if not stack_id:
        return JsonResponse(
            {"error": "Stack ID is required."},
            status=400
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
        return JsonResponse(
            {"error": "Failed to initialize Google Cloud Storage client."},
            status=500
        )

    bucket_name = "deploy_box_bucket"
    blob_name = f"{stack.stack.type.upper()}.tar"

    try:
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # Ensure the file exists before attempting to download
        if not blob.exists(client):
            return JsonResponse(
                {"error": f"Stack file '{blob_name}' not found in bucket '{bucket_name}'."},
                status=404
            )

        # Stream the file response instead of loading everything into memory
        response = FileResponse(blob.open("rb"), content_type="application/x-tar")
        response["Content-Disposition"] = f'attachment; filename="{blob_name}"'
        return response

    except Exception as e:
        logger.error(f"Error downloading stack {stack_id}: {e}")
        return JsonResponse(
            {"error": f"An error occurred while downloading the stack: {str(e)}"},
            status=500
        )
    

def update_database_storage_billing(request: HttpRequest) -> JsonResponse:
    data = request.data

    for stack_id, usage in data.items():
        StackDatabases.objects.filter(stack_id=stack_id).update(current_usage=F('current_usage')+usage)



    return JsonResponse(
        {
            "message": "Database storage billing updated successfully.",
            "data": data
        },
        status=200
    )

