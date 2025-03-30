from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from api.services import stack_services
from accounts.decorators.oauth_required import oauth_required

DEPLOY_BOX_API_URL = "http://34.68.6.54:5000/api"
# DEPLOY_BOX_API_URL = "http://localhost:5000/api"


@api_view(["GET"])
def testing(request: Request):
    # gcp_utils.create_service_account('6')

    return Response({"message": "Testing"}, status=status.HTTP_200_OK)


@api_view(["GET", "POST", "PATCH"])
def stack_operations(request: Request, stack_id=None):
    # GET: Fetch available stacks or a specific stack
    if request.method == "GET":
        if request.path.endswith("/download"):
            return stack_services.download_stack(request, stack_id)
        else:
            return stack_services.get_stacks(request, stack_id)

    # POST: Add a new stack
    elif request.method == "POST":
        if request.path.endswith("/deploy"):
            return stack_services.deploy_stack(request, stack_id)
        else:
            return stack_services.add_stack(request)

    # PATCH: Update a stack
    elif request.method == "PATCH":
        return stack_services.update_stack(request, stack_id)
    
@api_view(["GET"])
@oauth_required
def get_all_stacks(request):
    return stack_services.get_all_stacks(request)

@api_view(["POST"])
def update_database_usage(request):
    return stack_services.update_database_storage_billing(request)

