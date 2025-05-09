from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from core.decorators import AuthHttpRequest
import stacks.services as services
from projects.models import Project
from stacks.models import PurchasableStack, Stack
from core.helpers import request_helpers


def get_stack(request: AuthHttpRequest) -> JsonResponse:
    return services.get_stack(request)


def post_stack(request: AuthHttpRequest) -> JsonResponse:
    try:

        project_id, purchasable_stack_id, name = request_helpers.assertRequestFields(
            request, ["project_id", "purchasable_stack_id", "name"]
        )
    except request_helpers.MissingFieldError as e:
        return e.to_response()

    project = get_object_or_404(Project, id=project_id)
    purchasable_stack = get_object_or_404(PurchasableStack, id=purchasable_stack_id)

    return services.add_stack(project, purchasable_stack, name)


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
        {"success": True, "message": "Stack deleted successfully."}, status=200
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
    return JsonResponse({"error": "Not implemented"}, status=501)


def delete_stack_env(request: AuthHttpRequest, stack_id: str) -> JsonResponse:
    return JsonResponse({"error": "Not implemented"}, status=501)
