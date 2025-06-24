import logging
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from typing import Union

from projects.models import Project, ProjectMember
from accounts.models import UserProfile
from organizations.models import Organization, OrganizationMember

logger = logging.getLogger(__name__)


def get_projects(user: UserProfile) -> JsonResponse:
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

def get_project(user: UserProfile, project_id: str) -> Union[Project, None]:
    project = Project.objects.filter(user=user, id=project_id).first()
    if not project:
        return None
    
    return project


def create_project(user: UserProfile, name: str, description: str, organization_id: str) -> Union[JsonResponse, HttpResponse]:
    try:
        # Check if the user is a member of the organization
        organization = get_object_or_404(Organization, id=organization_id)
        get_object_or_404(OrganizationMember, organization=organization, user=user)

        # Create the project
        project = Project.objects.create(name=name, description=description, organization=organization)

        # Add the user as a member of the project
        ProjectMember.objects.create(user=user, project=project, role="admin")

        check_project = Project.objects.get(name=name, organization=organization)

        if check_project:

            return redirect(reverse('main_site:organization_dashboard', args=[organization_id]))

        else:
            return JsonResponse({"message": "project does not exist"}, status=400)

    except Exception as e:
        return JsonResponse({"message": f'an unexpected error occured {e}'}, status=400)

def update_project(project_id: int, name: str, description: str, user: UserProfile) -> JsonResponse:
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

def delete_project(project_id: str, user: UserProfile) -> JsonResponse:
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        logger.error(f"Project not found: {project_id}")
        return JsonResponse({"error": "Project not found"}, status=404)

    # Check if the user is a member of the project
    if not ProjectMember.objects.filter(user=user, project=project).exists():
        return JsonResponse({"error": "You are not a member of this project"}, status=403)

    # Delete the project
    project.delete()

    return JsonResponse({"message": "Project deleted successfully"})
