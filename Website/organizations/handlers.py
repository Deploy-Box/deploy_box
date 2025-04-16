import json
from django.http import JsonResponse

import organizations.services as services
from core.decorators import AuthHttpRequest
from core.helpers import assertRequestFields
from .forms import OrganizationCreateFormWithMembers


def get_organizations(request: AuthHttpRequest) -> JsonResponse:
    user = request.auth_user

    return services.get_organizations(user)

def get_organization(request: AuthHttpRequest, organization_id: str) -> JsonResponse:
    user = request.auth_user

    return services.get_organization(user, organization_id)

def create_organization(request: AuthHttpRequest) -> JsonResponse:


    form = OrganizationCreateFormWithMembers(request.POST)

    if form.is_valid():

        user = request.auth_user

        response = assertRequestFields(request, ["name", "email"], ["member", "role"], mimetype='application/x-www-form-urlencoded')


        if isinstance(response, JsonResponse):
            return response

        name, email, member, role = response

        print(response)

        return services.create_organization(user, name, email, member, role)

    else:
        return JsonResponse({"message": "form is not valid"}, status=400)

def update_organization(request: AuthHttpRequest, organization_id: str) -> JsonResponse:
    user = request.auth_user
    data = json.loads(request.body)

    return services.update_organization(user, organization_id, data)

def delete_organization(request: AuthHttpRequest, organization_id: str) -> JsonResponse:
    user = request.auth_user

    return services.delete_organization(user, organization_id)
