from django.http import HttpResponse, JsonResponse, FileResponse

from core.decorators import oauth_required, AuthHttpRequest
import projects.handlers as handlers


@oauth_required()
def base_routing(
    request: AuthHttpRequest,
) -> JsonResponse | HttpResponse:
    if request.method == "GET":
        return handlers.get_projects(request)

    elif request.method == "POST":
        return handlers.create_project(request)

    else:
        return JsonResponse(
            {"error": "Method not allowed"}, status=405
        )

@oauth_required()
def specific_routing(
    request: AuthHttpRequest,
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