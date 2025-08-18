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
        return handlers.add_org_member(request, organization_id)
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

# Project transfer views
@oauth_required()
def initiate_project_transfer(
    request: AuthHttpRequest,
    project_id: str,
) -> JsonResponse:
    if request.method == "POST":
        return handlers.initiate_project_transfer(request, project_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

@oauth_required()
def accept_project_transfer(
    request: AuthHttpRequest,
    transfer_id: str,
) -> JsonResponse:
    if request.method == "POST":
        return handlers.accept_project_transfer(request, transfer_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

@oauth_required()
def get_project_transfer_status(
    request: AuthHttpRequest,
    transfer_id: str,
) -> JsonResponse:
    if request.method == "GET":
        return handlers.get_project_transfer_status(request, transfer_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

@oauth_required()
def get_user_transfer_invitations(
    request: AuthHttpRequest,
) -> JsonResponse:
    if request.method == "GET":
        return handlers.get_user_transfer_invitations(request)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

@oauth_required()
def cancel_project_transfer(
    request: AuthHttpRequest,
    transfer_id: str,
) -> JsonResponse:
    if request.method == "POST":
        return handlers.cancel_project_transfer(request, transfer_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

@oauth_required()
def transfer_project_to_organization(
    request: AuthHttpRequest,
    project_id: str,
) -> JsonResponse:
    if request.method == "POST":
        return handlers.transfer_project_to_organization(request, project_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)