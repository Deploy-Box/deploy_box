import logging
from django.http import JsonResponse
from django.db import transaction
from django.shortcuts import get_object_or_404

from projects.services import create_project
from accounts.models import User
from organizations.models import Organization, OrganizationMember
from payments.views import create_stripe_user

logger = logging.getLogger(__name__)


def get_organizations(user: User) -> JsonResponse:
    organization_members = OrganizationMember.objects.filter(user=user).values_list("organization", flat=True)
    organization = Organization.objects.filter(id__in=organization_members).values(
        "id",
        "name",
        "created_at",
        "updated_at",
    )

    # Check if the user is a member of any project
    if not organization.exists():
        return JsonResponse({"data": []})

    return JsonResponse({"data": list(organization)})

def get_organization(user: User, organization_id: str) -> JsonResponse:
    organization = get_object_or_404(Organization, id=organization_id)

    # Check if the user is a member of the organization
    if not OrganizationMember.objects.filter(user=user, organization=organization).exists():
        return JsonResponse({"error": "You are not a member of this organization"}, status=403)

    return JsonResponse({
        "id": organization.id,
        "name": organization.name,
    })


def create_organization(user: User, name: str, email: str, member:str | None, role: str) -> JsonResponse:
    try:
        with transaction.atomic():
            print("inside transaction")
            stripe_customer_id = create_stripe_user(name=name, email=email)

            organization = Organization.objects.create(
                            name=name, email=email, stripe_customer_id=stripe_customer_id
                        )
            OrganizationMember.objects.create(user=user, organization=organization, role="admin")

            if member:
                print("inside member")
                user_id = User.objects.get(username=member)
                OrganizationMember.objects.create(user=user_id, organization=organization, role=role)

            create_project(
                name="Default Project",
                organization_id=organization.id,
                user=user,
                description="This is the default project created for you.",
            )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({
        "id": organization.id,
        "name": organization.name,
    })


def update_organization(user: User, organization_id: str, data: dict) -> JsonResponse:
    organization = get_object_or_404(Organization, id=organization_id)

    # Check if the user is an admin of the organization
    if not OrganizationMember.objects.filter(user=user, organization=organization, role="admin").exists():
        return JsonResponse({"error": "You are not authorized to update this organization"}, status=403)

    organization.name = data.get("name", organization.name)
    organization.email = data.get("email", organization.email)
    organization.stripe_customer_id = data.get("stripe_customer_id", organization.stripe_customer_id)
    organization.save()

    return JsonResponse({
        "id": organization.id,
        "name": organization.name,
        "email": organization.email,
    })


def delete_organization(user: User, organization_id: str) -> JsonResponse:
    organization = get_object_or_404(Organization, id=organization_id)

    # Check if the user is an admin of the organization
    if not OrganizationMember.objects.filter(user=user, organization=organization, role="admin").exists():
        return JsonResponse({"error": "You are not authorized to delete this organization"}, status=403)

    # TODO: Check if the organization has any projects

    organization.delete()

    return JsonResponse({"message": "organization deleted"}, status=200)

