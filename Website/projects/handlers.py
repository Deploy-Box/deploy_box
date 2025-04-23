from django.http import HttpResponse, JsonResponse

from core.decorators import AuthHttpRequest
from core.helpers import request_helpers
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

        try:
            name, description, organization_id = request_helpers.assertRequestFields(request, ["name", "description", "organization"], mimetype="application/json")
        except request_helpers.MissingFieldError as e:
            return e.to_response()
  
        return services.create_project(user, name, description, organization_id)

    except Exception as e:
        return JsonResponse({"message": f'An unexpected error occured {e}'}, status=400)

def delete_project(request: AuthHttpRequest, project_id: str) -> JsonResponse:
    user = request.auth_user

    return services.delete_project(user=user, project_id=project_id)