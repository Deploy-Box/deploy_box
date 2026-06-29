import json
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import logging

import organizations.services as services
from organizations.services import ServiceError
from core.helpers import request_helpers
from organizations.forms import OrganizationCreateFormWithMembers
from organizations.models import OrganizationMember, Organization
from organizations.helpers import check_permission
from accounts.models import UserProfile

logger = logging.getLogger(__name__)


def _json_error(exc: ServiceError) -> JsonResponse:
    """Convert a ServiceError into a JsonResponse."""
    return JsonResponse({"message": str(exc)}, status=exc.status_code)


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

    try:
        result = services.update_organization(user, organization_id, data)
    except ServiceError as exc:
        return _json_error(exc)
    return JsonResponse(result, status=200)

def delete_organization(request: HttpRequest, organization_id: str) -> JsonResponse:
    user = request.user

    try:
        result = services.delete_organization(user, organization_id)
    except ServiceError as exc:
        return _json_error(exc)
    return JsonResponse(result, status=200)

def update_user(request: HttpRequest, organization_id: str, user_id: str) -> JsonResponse:
    user = request.user
    organization = Organization.objects.get(id=organization_id)

    try:
        result = services.update_user(user, organization, user_id)
    except ServiceError as exc:
        return _json_error(exc)
    return JsonResponse(result, status=200)

def add_org_members(request: HttpRequest, organization_id: str) -> JsonResponse:
        try:
            member, role = request_helpers.assertRequestFields(request, ["member", "role"], mimetype='application/x-www-form-urlencoded')
        except request_helpers.MissingFieldError as e:
            return JsonResponse({"message": e.message}, status=400)

        user = request.user
        organization = Organization.objects.get(id=organization_id)

        try:
            result = services.add_org_member(user, str(organization.id), member, role)
        except ServiceError as exc:
            return _json_error(exc)
        return JsonResponse(result, status=200)

def remove_org_member(request: HttpRequest, organization_id: str, user_id: str) -> JsonResponse:
    user = request.user
    try:
        result = services.remove_org_member(user, organization_id, user_id)
    except ServiceError as exc:
        return _json_error(exc)
    return JsonResponse(result, status=200)

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

    try:
        result = services.invite_new_user_to_org(user, organization, email)
    except ServiceError as exc:
        return _json_error(exc)
    return JsonResponse(result, status=200)

def leave_organization(request: HttpRequest, organization_id: str) -> JsonResponse:
    """Handler for users to leave an organization themselves."""
    user = request.user
    try:
        result = services.leave_organization(user, organization_id)
    except ServiceError as exc:
        return _json_error(exc)
    return JsonResponse(result, status=200)

def remove_pending_invite(request: HttpRequest, organization_id: str, invite_id: str) -> JsonResponse:
    """Handler for removing pending invites from an organization."""
    user = request.user
    try:
        result = services.remove_pending_invite(user, organization_id, invite_id)
    except ServiceError as exc:
        return _json_error(exc)
    return JsonResponse(result, status=200)

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

    try:
        result = services.initiate_project_transfer(
            user=user,
            project_id=project_id,
            client_email=client_email,
            client_name=client_name,
            client_company=client_company,
            keep_developer=keep_developer,
        )
    except ServiceError as exc:
        return _json_error(exc)
    return JsonResponse(result, status=200)

def accept_project_transfer(request: HttpRequest, transfer_id: str) -> JsonResponse:
    """Accept a project ownership transfer"""
    user = request.user
    try:
        result = services.accept_project_transfer(transfer_id, user)
    except ServiceError as exc:
        return _json_error(exc)
    return JsonResponse(result, status=200)

def get_project_transfer_status(request: HttpRequest, transfer_id: str) -> JsonResponse:
    """Get the status of a project transfer invitation"""
    try:
        result = services.get_project_transfer_status(transfer_id)
    except ServiceError as exc:
        return _json_error(exc)
    return JsonResponse(result, status=200)

def get_user_transfer_invitations(request: HttpRequest) -> JsonResponse:
    """Get all transfer invitations for the current user"""
    user = request.user
    try:
        result = services.get_user_transfer_invitations(user)
    except ServiceError as exc:
        return _json_error(exc)
    return JsonResponse(result, status=200)

def cancel_project_transfer(request: HttpRequest, transfer_id: str) -> JsonResponse:
    """Cancel a project transfer invitation"""
    user = request.user
    try:
        result = services.cancel_project_transfer(user, transfer_id)
    except ServiceError as exc:
        return _json_error(exc)
    return JsonResponse(result, status=200)

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

    try:
        result = services.transfer_project_to_organization(
            user=user,
            project_id=project_id,
            target_organization_id=target_organization_id,
            keep_developer=keep_developer,
        )
    except ServiceError as exc:
        return _json_error(exc)
    return JsonResponse(result, status=200)
