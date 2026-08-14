from django.http import HttpRequest, HttpResponse, JsonResponse

from core.helpers import request_helpers
import projects.services as services
from typing import Union


def get_projects(request: HttpRequest) -> JsonResponse:
    user = request.user

    return services.get_projects(user)

def get_project(request: HttpRequest, project_id: str) -> JsonResponse:
    user = request.user

    project = services.get_project(user, project_id)

    if project is None:
        return JsonResponse({"message": "Project not found"}, status=404)
    
    return JsonResponse(project, status=200)


def create_project(request: HttpRequest) -> Union[JsonResponse, HttpResponse]:
    try:
        user = request.user

        try:
            name, description, organization_id = request_helpers.assertRequestFields(request, ["name", "description", "organization"], mimetype="application/json")
        except request_helpers.MissingFieldError as e:
            return e.to_response()
  
        return services.create_project(user, name, description, organization_id)

    except Exception as e:
        return JsonResponse({"message": f'An unexpected error occured {e}'}, status=400)

def delete_project(request: HttpRequest, project_id: str) -> JsonResponse:
    user = request.user

    return services.delete_project(user=user, project_id=project_id)