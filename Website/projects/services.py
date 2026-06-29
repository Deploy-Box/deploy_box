"""
Projects service layer — business logic for project CRUD.

Returns plain data (dicts, model instances) or raises ServiceError exceptions.
Never imports Response, JsonResponse, or HttpResponse.
"""
import logging
from django.shortcuts import get_object_or_404

from projects.models import Project, ProjectMember
from accounts.models import UserProfile
from organizations.models import Organization, OrganizationMember

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


class NotFoundError(ServiceError):
    def __init__(self, message="Not found"):
        super().__init__(message, status_code=404)


class ForbiddenError(ServiceError):
    def __init__(self, message="Forbidden"):
        super().__init__(message, status_code=403)


def get_projects(user: UserProfile) -> list[dict]:
    """Return all projects the user is a member of."""
    project_ids = ProjectMember.objects.filter(user=user).values_list("project", flat=True)
    projects = Project.objects.filter(id__in=project_ids).values(
        "id", "name", "description", "created_at", "updated_at",
    )
    return list(projects)


def get_project(user: UserProfile, project_id: str) -> dict | None:
    """Return a single project if the user has access."""
    project = Project.objects.filter(user=user, id=project_id).first()
    if not project:
        return None
    return project


def create_project(
    user: UserProfile,
    name: str,
    description: str = "",
    organization_id: str = "",
) -> dict:
    """
    Create a project under an organization.
    Raises ForbiddenError if user is not a member or free-tier limit reached.
    """
    organization = get_object_or_404(Organization, id=organization_id)
    if not OrganizationMember.objects.filter(organization=organization, user=user).exists():
        raise ForbiddenError("You are not a member of this organization")

    if organization.has_reached_free_project_limit():
        raise ForbiddenError(
            "Free plan is limited to 1 project per organization. "
            "Please upgrade to create more projects."
        )

    project = Project.objects.create(
        name=name, description=description, organization=organization,
    )
    ProjectMember.objects.create(user=user, project=project, role="admin")

    return {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "organization_id": str(organization.id),
    }


def update_project(project_id: str, name: str, description: str, user: UserProfile) -> dict:
    """Update project name/description. Raises NotFoundError or ForbiddenError."""
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        raise NotFoundError("Project not found")

    if not ProjectMember.objects.filter(user=user, project=project).exists():
        raise ForbiddenError("You are not a member of this project")

    project.name = name
    project.description = description
    project.save()

    return {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def delete_project(project_id: str, user: UserProfile) -> dict:
    """Delete a project. Raises NotFoundError or ForbiddenError."""
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        raise NotFoundError("Project not found")

    if not ProjectMember.objects.filter(user=user, project=project).exists():
        raise ForbiddenError("You are not a member of this project")

    project.delete()
    return {"message": "Project deleted successfully"}
