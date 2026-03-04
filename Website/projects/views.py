from django.http import HttpRequest, HttpResponse, JsonResponse, FileResponse

import projects.handlers as handlers
from typing import Union


def base_routing(
    request: HttpRequest,
) -> Union[JsonResponse, HttpResponse]:
    if request.method == "GET":
        return handlers.get_projects(request)

    elif request.method == "POST":
        return handlers.create_project(request)

    else:
        return JsonResponse(
            {"error": "Method not allowed"}, status=405
        )

def specific_routing(
    request: HttpRequest,
    project_id: str,
) -> JsonResponse:
    if request.method == "GET":
        return handlers.get_project(request, project_id)

    elif request.method == "DELETE":
        return handlers.delete_project(request, project_id)

    else:
        return JsonResponse(
            {"error": "Method not allowed"}, status=405
        )