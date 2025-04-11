from django.http import JsonResponse, HttpRequest, FileResponse  # type: ignore

from api.services import stack_services, GCP_services
from core.decorators import oauth_required, AuthHttpRequest
from core.helpers import assertRequiredFields

@oauth_required()
def stack_operations(
    request: AuthHttpRequest,
    organization_id: str | None = None,
    project_id: str | None = None,
    stack_id: str | None = None,
) -> JsonResponse | FileResponse:
    # GET: Fetch available stacks or a specific stack
    if request.method == "GET":
        if request.path.endswith("/download"):
            return stack_services.download_stack(request, stack_id)
        else:
            if stack_id is None:
                return stack_services.get_stacks(request)
            else:
                assert organization_id is not None, "Organization ID is required."
                assert project_id is not None, "Project ID is required."
                return stack_services.get_stack(
                    request, organization_id, project_id, stack_id
                )

    # POST: Add a new stack
    elif request.method == "POST":
        if request.path.endswith("/deploy"):
            return stack_services.deploy_stack(request, stack_id)
        else:
            user = request.auth_user

            response = assertRequiredFields(
                request, ["project_id", "available_stack_id", "name"]
            )

            if isinstance(response, JsonResponse):
                return response

            project_id, available_stack_id, name = response

            return stack_services.add_stack(user, project_id, available_stack_id, name)

    # PATCH: Update a stack
    elif request.method == "PATCH":
        return stack_services.update_stack(request, stack_id)

    # If the request method is not handled, return a 405 Method Not Allowed
    return JsonResponse({"error": "Method not allowed."}, status=405)


@oauth_required()
def get_all_stacks(request: AuthHttpRequest) -> JsonResponse:
    return stack_services.get_all_stacks(request)


@oauth_required()
def get_stack(
    request: HttpRequest, organization_id: str, project_id: str, stack_id: str
) -> JsonResponse:
    return stack_services.get_stack(request, organization_id, project_id, stack_id)


def update_database_usage(request: HttpRequest) -> JsonResponse:
    return stack_services.update_database_storage_billing(request)


def get_usage_per_stack_from_db(request):
    return stack_services.get_database_current_use_from_db(request)


@oauth_required()
def update_cpu_billing(request: HttpRequest) -> JsonResponse:
    return GCP_services.update_billing_cpu(request)
