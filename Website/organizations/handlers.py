import json
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import logging

import organizations.services as services
from core.helpers import request_helpers
from organizations.forms import OrganizationCreateFormWithMembers
from organizations.models import OrganizationMember, Organization
from organizations.helpers import check_permission
from accounts.models import UserProfile

logger = logging.getLogger(__name__)

def get_organizations(request: HttpRequest) -> JsonResponse:
    user = request.user
    organizations = services.get_organizations(user)

    if not organizations:
        return JsonResponse({"message": "organizations not found"}, status=404)

    return JsonResponse(organizations, status=200)

def get_organization(request: HttpRequest, organization_id: str) -> JsonResponse:
    user = request.user

    organization = services.get_organization(user, organization_id)

    if not organization:
        return JsonResponse({"message": "organization not found"}, status=404)

    return JsonResponse(organization, status=200)

def create_organization(request: HttpRequest) -> JsonResponse:
    user = request.user
    
    # Automatically use the authenticated user's email
    data = {**dict(request.POST), 'email': user.email}
    form = OrganizationCreateFormWithMembers(data)

    if form.is_valid():
        try:
            name, _, _ = request_helpers.assertRequestFields(request, ["name"], ["member", "role"], mimetype='application/x-www-form-urlencoded')
        except request_helpers.MissingFieldError as e:
            return JsonResponse({"message": e.message}, status=400)

        # Use the email from the authenticated user
        organization = services.create_organization(user, name, user.email)

        return JsonResponse(organization, status=201)

    else:
        return JsonResponse({"message": "form is not valid"}, status=400)

def update_organization(request: HttpRequest, organization_id: str) -> JsonResponse:
    user = request.user
    data = json.loads(request.body)
    assert(data != None)

    return services.update_organization(user, organization_id, data)

def delete_organization(request: HttpRequest, organization_id: str) -> JsonResponse:
    user = request.user

    return services.delete_organization(user, organization_id)

def update_user(request: HttpRequest, organization_id: str, user_id: str) -> JsonResponse:
    user = request.user
    organization = Organization.objects.get(id=organization_id)
    is_admin = OrganizationMember.objects.filter(organization=organization, user=user, role='admin').exists()

    if is_admin:
        return services.update_user(user, organization, user_id)
    else:
        return JsonResponse({"message": "you must be an org admin to remove members"}, status=400)

def add_org_members(request: HttpRequest, organization_id: str) -> JsonResponse:
        try:
            member, role = request_helpers.assertRequestFields(request, ["member", "role"], mimetype='application/x-www-form-urlencoded')
        except request_helpers.MissingFieldError as e:
            return JsonResponse({"message": e.message}, status=400)

        user = request.user
        organization = Organization.objects.get(id=organization_id)

        return services.add_org_members(member, role, organization, user)

def remove_org_member(request: HttpRequest, organization_id: str, user_id: str) -> JsonResponse:
    user = request.user
    return services.remove_org_member(user, organization_id, user_id)

def invite_new_user_to_org(request: HttpRequest, organization_id: str) -> JsonResponse:
    user = request.user

    try:
        email, = request_helpers.assertRequestFields(request, ["email"], mimetype='application/x-www-form-urlencoded')
    except request_helpers.MissingFieldError as e:
        return JsonResponse({"message": e.message}, status=400)

    try:

        organization = check_permission.check_permisssion(user, organization_id, requeired_role="admin")

    except check_permission.OrganizationPermissionsError as e:
        return e.to_response()

    return services.invite_new_user_to_org(user, organization, email)

def leave_organization(request: HttpRequest, organization_id: str) -> JsonResponse:
    """
    Handler for users to leave an organization themselves.
    """
    user = request.user
    return services.leave_organization(user, organization_id)

def remove_pending_invite(request: HttpRequest, organization_id: str, invite_id: str) -> JsonResponse:
    """
    Handler for removing pending invites from an organization.
    """
    user = request.user
    return services.remove_pending_invite(user, organization_id, invite_id)

def initiate_project_transfer(request: HttpRequest, project_id: str) -> JsonResponse:
    """Initiate a project ownership transfer to a client"""
    user = request.user

    try:
        data = json.loads(request.body)
        client_email = data.get("client_email")
        client_name = data.get("client_name")
        client_company = data.get("client_company")
        keep_developer = data.get("keep_developer", True)
        
        if not client_email or not client_name:
            return JsonResponse({"message": "client_email and client_name are required"}, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"message": f"Error parsing request data: {e}"}, status=400)

    return services.initiate_project_transfer(
        user=user,
        project_id=project_id,
        client_email=client_email,
        client_name=client_name,
        client_company=client_company,
        keep_developer=keep_developer
    )

def accept_project_transfer(request: HttpRequest, transfer_id: str) -> JsonResponse:
    """Accept a project ownership transfer"""
    user = request.user
    return services.accept_project_transfer(transfer_id, user)

def get_project_transfer_status(request: HttpRequest, transfer_id: str) -> JsonResponse:
    """Get the status of a project transfer invitation"""
    return services.get_project_transfer_status(transfer_id)

def get_user_transfer_invitations(request: HttpRequest) -> JsonResponse:
    """Get all transfer invitations for the current user"""
    user = request.user
    return services.get_user_transfer_invitations(user)

def cancel_project_transfer(request: HttpRequest, transfer_id: str) -> JsonResponse:
    """Cancel a project transfer invitation"""
    user = request.user
    return services.cancel_project_transfer(user, transfer_id)

def transfer_project_to_organization(request: HttpRequest, project_id: str) -> JsonResponse:
    """Transfer a project to another organization"""
    user = request.user

    try:
        data = json.loads(request.body)
        target_organization_id = data.get("target_organization_id")
        keep_developer = data.get("keep_developer", True)
        
        if not target_organization_id:
            return JsonResponse({"message": "target_organization_id is required"}, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"message": f"Error parsing request data: {e}"}, status=400)

    return services.transfer_project_to_organization(
        user=user,
        project_id=project_id,
        target_organization_id=target_organization_id,
        keep_developer=keep_developer
    )




