import logging
from django.http import JsonResponse
from django.db import transaction
from django.shortcuts import get_object_or_404

from projects.models import Project, ProjectMember
from accounts.models import User
from organizations.models import Organization, OrganizationMember

logger = logging.getLogger(__name__)


def get_projects(user: User) -> JsonResponse:
    project_members = ProjectMember.objects.filter(user=user).values_list("project", flat=True)
    projects = Project.objects.filter(id__in=project_members).values(
        "id",
        "name",
        "description",
        "created_at",
        "updated_at",
    )

    # Check if the user is a member of any project
    if not projects.exists():
        return JsonResponse({"data": []})

    return JsonResponse({"data": list(projects)})

def get_project(user: User, project_id: str) -> JsonResponse:
    project = get_object_or_404(Project, id=project_id)

    # Check if the user is a member of the project
    if not ProjectMember.objects.filter(user=user, project=project).exists():
        return JsonResponse({"error": "You are not a member of this project"}, status=403)

    return JsonResponse({
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    })

def create_project(user: User, name: str, description: str, organization_id: str) -> JsonResponse:
    # Check if the user is a member of the organization
    organization = get_object_or_404(Organization, id=organization_id)
    get_object_or_404(OrganizationMember, organization=organization, user=user)

    # Create the project
    project = Project.objects.create(name=name, description=description, organization=organization)

    # Add the user as a member of the project
    ProjectMember.objects.create(user=user, project=project, role="admin")

    return JsonResponse({
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    })

def update_project(project_id: int, name: str, description: str, user: User) -> JsonResponse:
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({"error": "Project not found"}, status=404)

    # Check if the user is a member of the project
    if not ProjectMember.objects.filter(user=user, project=project).exists():
        return JsonResponse({"error": "You are not a member of this project"}, status=403)

    # Update the project
    project.name = name
    project.description = description
    project.save()

    return JsonResponse({
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    })

def delete_project(project_id: int, user: User) -> JsonResponse:
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({"error": "Project not found"}, status=404)

    # Check if the user is a member of the project
    if not ProjectMember.objects.filter(user=user, project=project).exists():
        return JsonResponse({"error": "You are not a member of this project"}, status=403)

    # Delete the project
    project.delete()

    return JsonResponse({"message": "Project deleted successfully"})
