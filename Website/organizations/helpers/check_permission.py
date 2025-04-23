from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from accounts.models import User
from organizations.models import Organization, OrganizationMember

class OrganizationPermissionsError(Exception):
    def __init__(self, message: str, status: int = 400):
        self.message = message
        self.status = status
        super().__init__(message)

    def to_response(self) -> JsonResponse:
        return JsonResponse({"error": self.message}, status=self.status)

def check_permisssion(user: User, organization_id, requeired_role: str | None) -> Organization:
    if requeired_role == None:
        organization = Organization.objects.get(id=organization_id)
        return organization
    elif requeired_role.lower() == "admin":
        organization_member = get_object_or_404(OrganizationMember, user=user, organization_id=organization_id, role="admin")
        return Organization.objects.get(organization_member=organization_member)

    raise OrganizationPermissionsError("You don't have permission to access this organization.", status=403)


