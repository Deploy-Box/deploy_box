from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from accounts.models import UserProfile
from organizations.models import Organization, OrganizationMember, PendingInvites


class ExamplesView(View):
    def example_organization_members(self, request: HttpRequest) -> HttpResponse:
        """Example organization members view."""

        # Mock data for example organization members view
        user = UserProfile(username="example_user", email="user@example.com")
        organization_id = "example_org_id"
        organization = Organization(id=organization_id, name="Example Organization", email="org@example.com")
        members = [
            OrganizationMember(user=user, organization=organization, role="admin"),
            OrganizationMember(user=UserProfile(username="member1", email="member1@example.com"), organization=organization, role="member"),
        ]
        pending_invites = [
            PendingInvites(email="invitee@example.com", organization=organization),
        ]
        user_organizations = [
            organization,
            Organization(id="org2", name="Another Org", email="another@example.com"),
        ]
        is_admin = True

        return render(
            request,
            "dashboard/organization_members.html",
            {
                "user": user,
                "organization": organization,
                "members": members,
                "pending_invites": pending_invites,
                "user_organizations": user_organizations,
                "current_organization_id": organization_id,
                "is_admin": is_admin,
            },
        )


examples_view = ExamplesView()
