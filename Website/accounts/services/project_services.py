import json

from django.contrib.auth.models import User  # type: ignore
from django.http import JsonResponse, HttpRequest  # type: ignore

from organizations.models import Organization
from projects.models import Project, ProjectMember


def get_project(user: User, organization_id: str, project_id: str) -> Project:
    return Project.objects.get(
        projectmember__user=user, organization_id=organization_id, id=project_id
    )


def create_project(request: HttpRequest) -> JsonResponse:
    try:
        data = json.loads(request.body)
        name = data.get("name").lower()
        description = data.get("description")
        org_id = data.get("org_id")

        check_project = Project.objects.filter(name=name).exists()

        if not check_project:

            Project.objects.create(
                name=name, description=description, organization_id=org_id
            )

            return JsonResponse({"message": "project has been created"}, status=200)

        else:
            return JsonResponse({"message": "project already exists"}, status=404)
    except Exception as e:
        return JsonResponse(
            {"error": f"An unexpected error occurred: {str(e)}"}, status=500
        )


def delete_project(request: HttpRequest) -> JsonResponse:
    try:
        data = json.loads(request.body)
        name = data.get("name").lower()
        org_id = data.get("org_id")

        project = Project.objects.filter(name=name, organization_id=org_id).first()

        if project:
            project.delete()

            return JsonResponse({"message": "project was deleted"}, status=200)
        else:
            return JsonResponse({"message": "project was not found"}, status=404)
    except Exception as e:
        return JsonResponse(
            {"error": f"An unexpected error occurred: {str(e)}"}, status=500
        )


def update_project(request: HttpRequest) -> JsonResponse:
    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")

        project = Project.objects.get(id=project_id)
        if project:
            project.name = data.get("name", project.name).lower()
            project.description = data.get("description", project.description)

            if "organization_id" in data:
                org_id = data.get("organization_id")
                org = Organization.objects.filter(id=org_id).first()

                if org:
                    project.organization = data.get(
                        "organization_id", project.organization
                    )
                else:
                    return JsonResponse(
                        {"message": "organization does not exist"}, status=404
                    )

            project.save()

            return JsonResponse({"message": "project updated"}, status=200)

        else:
            return JsonResponse({"message": "project does not exist"}, status=404)
    except Exception as e:
        return JsonResponse(
            {"error": f"An unexpected error occurred: {str(e)}"}, status=500
        )


def add_project_members(request: HttpRequest) -> JsonResponse:
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        project_id = data.get("project_id")

        project = Project.objects.filter(id=project_id).first()
        project_member = ProjectMember.objects.filter(
            project_id=project_id, user_id=user_id
        ).first()

        if project:
            if not project_member:
                ProjectMember.objects.create(user_id=user_id, project_id=project_id)

                return JsonResponse({"message": "member has been added"}, status=200)
            else:
                return JsonResponse(
                    {"message": "project member already exists"}, status=404
                )
        else:
            return JsonResponse({"message": "project does not exist"}, status=404)
    except Exception as e:
        return JsonResponse(
            {"error": f"An unexpected error occurred: {str(e)}"}, status=500
        )


def delete_project_member(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_id = data.get("user_id")
            project_id = data.get("project_id")

            project_member = ProjectMember.objects.filter(
                user_id=user_id, project_id=project_id
            ).first()

            if project_member:
                project_member.delete()

                return JsonResponse(
                    {"message": "user has been removed from the project"}
                )
            else:
                return JsonResponse(
                    {"message": "user is not associated with this project"}
                )
        except Exception as e:
            return JsonResponse(
                {"message": f"An unexpected error occurred: {str(e)}"}, status=500
            )
