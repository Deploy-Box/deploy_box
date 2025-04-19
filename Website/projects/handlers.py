from django.http import HttpResponse, JsonResponse

from core.decorators import AuthHttpRequest
from core.helpers import assertRequestFields
import projects.services as services


def get_projects(request: AuthHttpRequest) -> JsonResponse:
    user = request.auth_user

    return services.get_projects(user)

def get_project(request: AuthHttpRequest, project_id: str) -> JsonResponse:
    user = request.auth_user

    return services.get_project(user, project_id)

def create_project(request: AuthHttpRequest) -> JsonResponse | HttpResponse:
    try:
        user = request.auth_user

        response = assertRequestFields(request, ["name", "description", "organization"], mimetype="application/x-www-form-urlencoded")

        if isinstance(response, JsonResponse):
            return response

        name, description, organization_id = response


        return services.create_project(user, name, description, organization_id)

    except Exception as e:
        return JsonResponse({"message": f'An unexpected error occured {e}'}, status=400)