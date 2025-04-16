from django.http import JsonResponse

import organizations.handlers as handlers
from core.decorators import oauth_required, AuthHttpRequest

@oauth_required()
def bulk_routing(
    request: AuthHttpRequest,
) -> JsonResponse:
    if request.method == "GET":
        return handlers.get_organizations(request)

    elif request.method == "POST":
        return handlers.create_organization(request)

    else:
        return JsonResponse(
            {"error": "Method not allowed"}, status=405
        )

@oauth_required()
def specific_routing(
    request: AuthHttpRequest,
    organization_id: str,
) -> JsonResponse:
    if request.method == "GET":
        return handlers.get_organization(request, organization_id)

    elif request.method == "PUT":
        return handlers.update_organization(request, organization_id)

    elif request.method == "DELETE":
        return handlers.delete_organization(request, organization_id)

    else:
        return JsonResponse(
            {"error": "Method not allowed"}, status=405
        )