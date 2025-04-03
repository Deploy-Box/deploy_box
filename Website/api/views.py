from django.http import JsonResponse, HttpRequest, FileResponse

from api.services import stack_services
from core.decorators import oauth_required

def stack_operations(request: HttpRequest, organization_id: str, project_id: str, stack_id: str | None = None) -> JsonResponse | FileResponse:
    # GET: Fetch available stacks or a specific stack
    if request.method == "GET":
        if request.path.endswith("/download"):
            return stack_services.download_stack(request, stack_id)
        else:
            if stack_id is None:
                return stack_services.get_stacks(request)
            else:
                return stack_services.get_stack(request, organization_id, project_id, stack_id)

    # POST: Add a new stack
    elif request.method == "POST":
        if request.path.endswith("/deploy"):
            return stack_services.deploy_stack(request, stack_id)
        else:
            return stack_services.add_stack(request)

    # PATCH: Update a stack
    elif request.method == "PATCH":
        return stack_services.update_stack(request, stack_id)
    
    # If the request method is not handled, return a 405 Method Not Allowed
    return JsonResponse(
        {"error": "Method not allowed."},
        status=405
    )
    
@oauth_required()
def get_all_stacks(request: HttpRequest) -> JsonResponse:
    return stack_services.get_all_stacks(request)

@oauth_required()
def get_stack(request: HttpRequest, organization_id: str, project_id: str, stack_id: str) -> JsonResponse:
    return stack_services.get_stack(request, organization_id, project_id, stack_id)

def update_database_usage(request: HttpRequest) -> JsonResponse:
    return stack_services.update_database_storage_billing(request)

def get_usage_per_stack_from_db(request):
    return stack_services.get_database_current_use_from_db(request)



