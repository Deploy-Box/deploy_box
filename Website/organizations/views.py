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

@oauth_required()
def update_user(
    request: AuthHttpRequest,
    organization_id: str,
    user_id: str
) -> JsonResponse:
    if request.method == "POST":
        return handlers.update_user(request, organization_id, user_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

@oauth_required()
def add_org_member(
    request: AuthHttpRequest,
    organization_id: str,
) -> JsonResponse:
    if request.method == "POST":
        return handlers.add_org_members(request, organization_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

@oauth_required()
def remove_org_member(
    request: AuthHttpRequest,
    organization_id: str,
    user_id: str
) -> JsonResponse:
    if request.method == "POST":
        return handlers.remove_org_member(request, organization_id, user_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

@oauth_required()
def invite_new_user_to_org(
    request: AuthHttpRequest,
    organization_id: str,
) -> JsonResponse:
    if request.method == "POST":
        return handlers.invite_new_user_to_org(request, organization_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

@oauth_required()
def leave_organization(
    request: AuthHttpRequest,
    organization_id: str
) -> JsonResponse:
    if request.method == "POST":
        return handlers.leave_organization(request, organization_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

@oauth_required()
def remove_pending_invite(
    request: AuthHttpRequest,
    organization_id: str,
    invite_id: str
) -> JsonResponse:
    if request.method == "POST":
        return handlers.remove_pending_invite(request, organization_id, invite_id)
    else:
        return JsonResponse({"success": False, "message": "method not allowed"}, status=405)