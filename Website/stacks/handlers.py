from django.http import JsonResponse, HttpRequest
from django.shortcuts import get_object_or_404

from .forms import EnvFileUploadForm
from core.decorators import AuthHttpRequest
import stacks.services as services
from projects.models import Project
from stacks.models import PurchasableStack, Stack
from core.helpers import request_helpers
from .serializers import StackDatabaseSerializer
from django.views.decorators.csrf import csrf_exempt


def get_stack(request: AuthHttpRequest) -> JsonResponse:
    print(f"Getting stack: {request.GET}")
    stack_id = request.GET.get("stack_id")
    if not stack_id:
        return JsonResponse({"error": "Stack ID is required"}, status=400)
    stack = services.get_stack(stack_id)
    return JsonResponse(stack)


def post_stack(request: AuthHttpRequest) -> JsonResponse:
    try:

        project_id, purchasable_stack_id, name = request_helpers.assertRequestFields(
            request, ["project_id", "purchasable_stack_id", "name"]
        )
    except request_helpers.MissingFieldError as e:
        return e.to_response()

    get_object_or_404(Project, id=project_id)
    get_object_or_404(PurchasableStack, id=purchasable_stack_id)

    stack = services.add_stack(
        project_id=project_id,
        purchasable_stack_id=purchasable_stack_id,
        name=name,
    )

    return JsonResponse({"success": True, "stack_id": stack.id})


def patch_stack(request: AuthHttpRequest, stack_id: str) -> JsonResponse:
    stack = get_object_or_404(Stack, id=stack_id)

    try:
        (root_directory,) = request_helpers.assertRequestFields(
            request, optional_fields=["root_directory"]
        )
    except request_helpers.MissingFieldError as e:
        return e.to_response()

    return JsonResponse({"success": services.update_stack(stack, root_directory)})


def delete_stack(request: AuthHttpRequest, stack_id: str) -> JsonResponse:
    stack = get_object_or_404(Stack, id=stack_id)

    stack_deleted = services.delete_stack(stack)

    if not stack_deleted:
        return JsonResponse({"error": "Failed to delete stack."}, status=500)

    return JsonResponse(
        {"success": True, "message": "Stack deleted successfully."}, status=204
    )


def get_stack_usage(request: AuthHttpRequest) -> JsonResponse:
    return JsonResponse({"error": "Not implemented"}, status=501)


def get_purchasable_stack(request: AuthHttpRequest) -> JsonResponse:
    return JsonResponse({"error": "Not implemented"}, status=501)


def post_purchasable_stack(request: AuthHttpRequest) -> JsonResponse:
    try:
        type, variant, version, price_id = request_helpers.assertRequestFields(
            request, ["type", "variant", "version", "price_id"]
        )
    except request_helpers.MissingFieldError as e:
        return e.to_response()

    # Check if the purchasable stack already exists
    purchasable_stack = PurchasableStack.objects.filter(price_id=price_id).first()

    if purchasable_stack:
        return JsonResponse({"error": "Purchasable stack already exists."}, status=400)

    return services.post_purchasable_stack(type, variant, version, price_id)


def patch_purchasable_stack(request: AuthHttpRequest) -> JsonResponse:
    return JsonResponse({"error": "Not implemented"}, status=501)


def delete_purchasable_stack(request: AuthHttpRequest) -> JsonResponse:
    return JsonResponse({"error": "Not implemented"}, status=501)


def get_stack_env(request: AuthHttpRequest, stack_id: str) -> JsonResponse:
    return JsonResponse({"error": "Not implemented"}, status=501)


def post_stack_env(request: AuthHttpRequest, stack_id: str) -> JsonResponse:

    form = EnvFileUploadForm(request.POST, request.FILES)
    if form.is_valid():
        selected_frameworks = form.cleaned_data["framework"]
        selected_locations = form.cleaned_data["select_location"]
        uploaded_file = form.cleaned_data["env_file"]

        return services.post_stack_env(
            stack_id, selected_frameworks, selected_locations, uploaded_file
        )
    else:
        return JsonResponse({"message": "you must upload a valid form"})


def delete_stack_env(request: AuthHttpRequest, stack_id: str) -> JsonResponse:
    return JsonResponse({"error": "Not implemented"}, status=501)


def get_all_stack_databases() -> JsonResponse:
    stack_databases = services.get_all_stack_databases()
    serializer = StackDatabaseSerializer(stack_databases, many=True)

    return JsonResponse(
        {"success": True, "data": serializer.data},
        status=200,
    )

@csrf_exempt
def update_stack_databases_usages(request: HttpRequest) -> JsonResponse:
    try:
        (data,) = request_helpers.assertRequestFields(request, ["data"])

    except request_helpers.MissingFieldError as e:
        return e.to_response()

    success = services.update_stack_databases_usages(data)

    if not success:
        return JsonResponse(
            {"error": "Failed to update stack databases usages."}, status=500
        )

    return JsonResponse({"success": True}, status=200)
