from accounts.models import Project
from django.contrib.auth.models import User

def get_project(user: User, organization_id: str, project_id: str) -> Project:
    return Project.objects.get(projectmember__user=user, organization_id=organization_id, id=project_id)
