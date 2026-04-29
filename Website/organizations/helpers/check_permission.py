from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from accounts.models import UserProfile
from organizations.models import Organization, OrganizationMember
from typing import Union

class OrganizationPermissionsError(Exception):
    def __init__(self, message: str, status: int = 400):
        self.message = message
        self.status = status
        super().__init__(message)

    def to_response(self) -> JsonResponse:
        return JsonResponse({"error": self.message}, status=self.status)

def check_permisssion(user: UserProfile, organization_id, requeired_role: Union[str, None]) -> Organization:
    if requeired_role is None:
        organization = Organization.objects.get(id=organization_id)
        return organization

    organization = get_object_or_404(Organization, id=organization_id)
    membership = OrganizationMember.objects.filter(
        user=user, organization=organization
    ).first()

    if not membership:
        raise OrganizationPermissionsError(
            "You don't have permission to access this organization.", status=403
        )

    if requeired_role.lower() == "admin" and membership.role != "admin":
        raise OrganizationPermissionsError(
            "Admin role required for this action.", status=403
        )

    return organization


