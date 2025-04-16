from django.http import JsonResponse, HttpRequest, FileResponse  # type: ignore

from api.services import stack_services, GCP_services
from api.models import StackBackend, StackFrontend, StackDatabase
from core.decorators import oauth_required, AuthHttpRequest
from core.helpers import assertRequestFields
from core.utils import GCPUtils


@oauth_required()
def stack_handler(
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

            response = assertRequestFields(
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
def delete_stack(request: AuthHttpRequest, stack_id: str) -> JsonResponse:
    return stack_services.delete_stack(request, stack_id)


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


@oauth_required()
def get_logs(
    request: HttpRequest, organization_id: str, project_id: str, stack_id: str
) -> JsonResponse:
    gcp_wrapper = GCPUtils()

    service_names = []

    stack_backend = StackBackend.objects.filter(stack_id=stack_id).first()
    if stack_backend is not None:
        service_names.append(f"backend-{stack_backend.id}")

    stack_frontend = StackFrontend.objects.filter(stack_id=stack_id).first()
    if stack_frontend is not None:
        service_names.append(f"frontend-{stack_frontend.id}")

    stack_database = StackDatabase.objects.filter(stack_id=stack_id).first()
    if stack_database is not None:
        service_names.append(f"database-{stack_database.id}")

    print(service_names)

    if len(service_names) == 0:
        return JsonResponse(
            {"status": "error", "message": "No service names found."}, status=400
        )

    return JsonResponse(gcp_wrapper.stream_logs(service_names))
