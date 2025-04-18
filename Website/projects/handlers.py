from django.http import JsonResponse

from core.decorators import AuthHttpRequest
from core.helpers import assertRequestFields
import projects.services as services


def get_projects(request: AuthHttpRequest) -> JsonResponse:
    user = request.auth_user

    return services.get_projects(user)

def get_project(request: AuthHttpRequest, project_id: str) -> JsonResponse:
    user = request.auth_user

    return services.get_project(user, project_id)

def create_project(request: AuthHttpRequest) -> JsonResponse:
    user = request.auth_user

    response = assertRequestFields(request, ["name", "description", "organization_id"])

    if isinstance(response, JsonResponse):
        return response

    name, description, organization_id = response


    return services.create_project(user, name, description, organization_id)