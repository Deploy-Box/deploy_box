from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from core.decorators import AuthHttpRequest
import stacks.services as services
from projects.models import Project
from stacks.models import PurchasableStack
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


def patch_stack(request: AuthHttpRequest) -> JsonResponse:
    return JsonResponse({"error": "Not implemented"}, status=501)


def delete_stack(request: AuthHttpRequest) -> JsonResponse:
    return JsonResponse({"error": "Not implemented"}, status=501)


def get_stack_usage(request: AuthHttpRequest) -> JsonResponse:
    return JsonResponse({"error": "Not implemented"}, status=501)


def get_purchasable_stack(request: AuthHttpRequest) -> JsonResponse:
    return JsonResponse({"error": "Not implemented"}, status=501)


def post_purchasable_stack(request: AuthHttpRequest) -> JsonResponse:

    try:
        type, variant, version, price_id = request_helpers.assertRequestFields(request, ["type", "variant", "version", "price_id"])
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
