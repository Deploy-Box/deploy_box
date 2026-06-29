from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response

from organizations.models import Organization
import organizations.handlers as handlers

def bulk_routing(
    request: HttpRequest,
) -> JsonResponse:
    if request.method == "GET":
        return handlers.get_organizations(request)

    elif request.method == "POST":
        return handlers.create_organization(request)

    else:
        return JsonResponse(
            {"error": "Method not allowed"}, status=405
        )

def specific_routing(
    request: HttpRequest,
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

def update_user(
    request: HttpRequest,
    organization_id: str,
    user_id: str
) -> JsonResponse:
    if request.method == "POST":
        return handlers.update_user(request, organization_id, user_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

def remove_org_member(
    request: HttpRequest,
    organization_id: str,
    user_id: str
) -> JsonResponse:
    if request.method == "POST":
        return handlers.remove_org_member(request, organization_id, user_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

def invite_new_user_to_org(
    request: HttpRequest,
    organization_id: str,
) -> JsonResponse:
    if request.method == "POST":
        return handlers.invite_new_user_to_org(request, organization_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

def leave_organization(
    request: HttpRequest,
    organization_id: str
) -> JsonResponse:
    if request.method == "POST":
        return handlers.leave_organization(request, organization_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

def remove_pending_invite(
    request: HttpRequest,
    organization_id: str,
    invite_id: str
) -> JsonResponse:
    if request.method == "POST":
        return handlers.remove_pending_invite(request, organization_id, invite_id)
    else:
        return JsonResponse({"success": False, "message": "method not allowed"}, status=405)

# Project transfer views
def initiate_project_transfer(
    request: HttpRequest,
    project_id: str,
) -> JsonResponse:
    if request.method == "POST":
        return handlers.initiate_project_transfer(request, project_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

def accept_project_transfer(
    request: HttpRequest,
    transfer_id: str,
) -> JsonResponse:
    if request.method == "POST":
        return handlers.accept_project_transfer(request, transfer_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

def get_project_transfer_status(
    request: HttpRequest,
    transfer_id: str,
) -> JsonResponse:
    if request.method == "GET":
        return handlers.get_project_transfer_status(request, transfer_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

def get_user_transfer_invitations(
    request: HttpRequest,
) -> JsonResponse:
    if request.method == "GET":
        return handlers.get_user_transfer_invitations(request)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

def cancel_project_transfer(
    request: HttpRequest,
    transfer_id: str,
) -> JsonResponse:
    if request.method == "POST":
        return handlers.cancel_project_transfer(request, transfer_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)

def transfer_project_to_organization(
    request: HttpRequest,
    project_id: str,
) -> JsonResponse:
    if request.method == "POST":
        return handlers.transfer_project_to_organization(request, project_id)
    else:
        return JsonResponse({"message": "method not allowed"}, status=405)
    
class OrganizationViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, pk=None):
        return Response({"organization": pk})

    def destroy(self, request, pk=None):
        from projects.models import Project

        organization = get_object_or_404(Organization, id=pk)

        if Project.objects.filter(organization=organization).exists():
            return Response(
                {
                    "error": "Cannot delete organization with active projects. "
                    "Please delete or transfer all projects first.",
                    "project_count": Project.objects.filter(organization=organization).count(),
                },
                status=400,
            )

        return handlers.delete_organization(request, pk)

    @action(detail=True, methods=["post"])
    def invite(self, request, pk=None):
        # Get the authenticated user from the request
        user = request.user
        
        # Get user data from request body
        user_data = request.data.get("user")

        print(user)
        print(user_data)
        return Response({"message": "Invite new user to organization"})


def update_billing_settings(request: HttpRequest, organization_id: str) -> JsonResponse:
    """Update billing/auto-pause settings for an organization (PATCH)."""
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    import json as _json
    from organizations.models import Organization

    try:
        org = Organization.objects.get(pk=organization_id)
    except Organization.DoesNotExist:
        return JsonResponse({"error": "Organization not found"}, status=404)

    try:
        body = _json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if "auto_pause_on_limit" in body:
        org.auto_pause_on_limit = bool(body["auto_pause_on_limit"])
    if "monthly_credit_allowance" in body:
        from decimal import Decimal, InvalidOperation
        try:
            val = Decimal(str(body["monthly_credit_allowance"]))
            if val < 0:
                return JsonResponse({"error": "Allowance must be non-negative"}, status=400)
            org.monthly_credit_allowance = val
        except (InvalidOperation, TypeError):
            return JsonResponse({"error": "Invalid allowance value"}, status=400)

    org.save(update_fields=["auto_pause_on_limit", "monthly_credit_allowance", "updated_at"])

    return JsonResponse({
        "auto_pause_on_limit": org.auto_pause_on_limit,
        "monthly_credit_allowance": str(org.monthly_credit_allowance),
    })
