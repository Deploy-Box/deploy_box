import json
from django.http import JsonResponse

import organizations.services as services
from core.decorators import AuthHttpRequest
from core.helpers import request_helpers
from organizations.forms import OrganizationCreateFormWithMembers
from organizations.models import OrganizationMember, Organization
from organizations.helpers import check_permission


def get_organizations(request: AuthHttpRequest) -> JsonResponse:
    user = request.auth_user
    organizations = services.get_organizations(user)

    if not organizations:
        return JsonResponse({"message": "organizations not found"}, status=404)

    return JsonResponse(organizations, status=200)

def get_organization(request: AuthHttpRequest, organization_id: str) -> JsonResponse:
    user = request.auth_user

    organization = services.get_organization(user, organization_id)

    if not organization:
        return JsonResponse({"message": "organization not found"}, status=404)

    return JsonResponse(organization, status=200)

def create_organization(request: AuthHttpRequest) -> JsonResponse:
    form = OrganizationCreateFormWithMembers(request.POST)

    if form.is_valid():
        try:
            name, email, _, _ = request_helpers.assertRequestFields(request, ["name", "email"], ["member", "role"], mimetype='application/x-www-form-urlencoded')
        except request_helpers.MissingFieldError as e:
            return JsonResponse({"message": e.message}, status=400)

        user = request.auth_user
        organization = services.create_organization(user, name, email)

        return JsonResponse(organization, status=201)

    else:
        return JsonResponse({"message": "form is not valid"}, status=400)

def update_organization(request: AuthHttpRequest, organization_id: str) -> JsonResponse:
    user = request.auth_user
    data = json.loads(request.body)
    assert(data != None)

    return services.update_organization(user, organization_id, data)

def delete_organization(request: AuthHttpRequest, organization_id: str) -> JsonResponse:
    user = request.auth_user

    return services.delete_organization(user, organization_id)

def update_user(request: AuthHttpRequest, organization_id: str, user_id: str) -> JsonResponse:
    user = request.auth_user
    organization = Organization.objects.get(id=organization_id)
    is_admin = OrganizationMember.objects.filter(organization=organization, user=user, role='admin').exists()

    if is_admin:
        return services.update_user(user, organization, user_id)
    else:
        return JsonResponse({"message": "you must be an org admin to remove members"}, status=400)

def add_org_members(request: AuthHttpRequest, organization_id: str) -> JsonResponse:
        try:
            member, role = request_helpers.assertRequestFields(request, ["member", "role"], mimetype='application/x-www-form-urlencoded')
        except request_helpers.MissingFieldError as e:
            return JsonResponse({"message": e.message}, status=400)

        user = request.auth_user
        organization = Organization.objects.get(id=organization_id)

        return services.add_org_members(member, role, organization, user)

def remove_org_member(request: AuthHttpRequest, organization_id: str, user_id: str) -> JsonResponse:

    user = request.auth_user

    return services.remove_org_member(user, organization_id, user_id)

def invite_new_user_to_org(request: AuthHttpRequest, organization_id: str) -> JsonResponse:
    user = request.auth_user

    try:
        email, = request_helpers.assertRequestFields(request, ["email"])
    except request_helpers.MissingFieldError as e:
        return JsonResponse({"message": e.message}, status=400)

    try:

        organization = check_permission.check_permisssion(user, organization_id, requeired_role="admin")

    except check_permission.OrganizationPermissionsError as e:
        return e.to_response()

    return services.invite_new_user_to_org(user, organization, email)




