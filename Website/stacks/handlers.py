from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from core.decorators import AuthHttpRequest
from core.helpers import assertRequiredFields
import stacks.services as services
from accounts.models import Project
from stacks.models import PurchasableStack


def get_stack(request: AuthHttpRequest) -> JsonResponse:
    pass


def post_stack(request: AuthHttpRequest) -> JsonResponse:
    response = assertRequiredFields(
        request, ["project_id", "purchasable_stack_id", "name"]
    )

    if isinstance(response, JsonResponse):
        return response

    project_id, purchasable_stack_id, name = response

    project = get_object_or_404(Project, id=project_id)
    purchasable_stack = get_object_or_404(PurchasableStack, id=purchasable_stack_id)

    return services.add_stack(project, purchasable_stack, name)


def patch_stack(request: AuthHttpRequest) -> JsonResponse:
    pass


def delete_stack(request: AuthHttpRequest) -> JsonResponse:
    pass


def get_stack_usage(request: AuthHttpRequest) -> JsonResponse:
    pass


def get_purchasable_stack(request: AuthHttpRequest) -> JsonResponse:
    pass


def post_purchasable_stack(request: AuthHttpRequest) -> JsonResponse:
    response = assertRequiredFields(request, ["type", "variant", "version", "price_id"])

    if isinstance(response, JsonResponse):
        return response

    type, variant, version, price_id = response

    # Check if the purchasable stack already exists
    purchasable_stack = PurchasableStack.objects.filter(price_id=price_id).first()

    if purchasable_stack:
        return JsonResponse({"error": "Purchasable stack already exists."}, status=400)

    return services.post_purchasable_stack(type, variant, version, price_id)


def patch_purchasable_stack(request: AuthHttpRequest) -> JsonResponse:
    pass


def delete_purchasable_stack(request: AuthHttpRequest) -> JsonResponse:
    pass
