import logging
from django.http import JsonResponse
from django.db import transaction
from django.shortcuts import get_object_or_404

from projects.services import create_project
from accounts.models import User
from organizations.models import Organization, OrganizationMember
from payments.views import create_stripe_user
from .helpers.email_helpers import invite_org_member

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

def update_user(user: User, organization: object, user_id: str) -> JsonResponse:
    permission_check = OrganizationMember.objects.filter(user=user, organization=organization, role="admin").exists()
    multiple_admin_check = OrganizationMember.objects.filter(organization=organization, role="admin")

    if not permission_check:
        return JsonResponse({"message": "you must be an admin of this org to update permissions"}, status=400)

    if len(multiple_admin_check) <= 1 and user.id == int(user_id): # type: ignore
        return JsonResponse({"message": "in order to downgrade your own permissions there must be more than one admin"}, status=400)

    try:
        org_user = User.objects.get(id=user_id)
        org_member = OrganizationMember.objects.get(organization=organization, user=org_user)

        if org_member.role.lower() == "admin":
            print("user is admin")
            org_member.role = "member"
            org_member.save()
            invite_org_member.send_user_permission_update_emaill(user=org_user, organization=organization)
            return JsonResponse({"message": "user permission updated successfully"}, status=200)
        else:
            org_member.role = "admin"
            org_member.save()
            invite_org_member.send_user_permission_update_emaill(user=org_user, organization=organization)
            return JsonResponse({"message": "user permission updated successfully"}, status=200)

    except Exception as e:
        return JsonResponse({"message": f'an unexpected error occured {e}'}, status=400)


def add_org_members(member: str, role: str, organization: object, user: User) -> JsonResponse:
    permission_check = OrganizationMember.objects.filter(user_id=user, organization=organization, role='admin').exists()

    if permission_check:
        user_to_add = User.objects.get(username=member)

        if not user_to_add:
            return JsonResponse({"message": "user could not be found please ensuer username is correct"}, status=404)

        member_check = OrganizationMember.objects.filter(organization=organization, user=user_to_add)

        if member_check:
            return JsonResponse({"message": "this user is already a member of this organization"}, status=200)

        OrganizationMember.objects.create(organization=organization, user=user_to_add, role=role)

        invite_org_member.send_invite_email(user_to_add, organization)

        return JsonResponse({"message": "user has been successfully added"}, status=200)

    else:
        return JsonResponse({"message": "you must be a admin of this org in order to add members"}, status=500)

def remove_org_member(user: User, organization_id: str, user_id: str) -> JsonResponse:
    permission_check = OrganizationMember.objects.filter(user_id=user, role='admin').exists()

    if permission_check:
        user_to_remove = OrganizationMember.objects.filter(id=user_id, organization_id=organization_id).first()
        organization = Organization.objects.get(id=organization_id)
        print(user_to_remove.user_id) # type: ignore
        user_to_email = User.objects.get(id=user_to_remove.user_id) # type: ignore

        invite_org_member.send_user_removed_email(user_to_email, organization)

        if not user_to_remove:
            return JsonResponse({"message", "user could not be found"}, status=404)


        user_to_remove.delete()

        return JsonResponse({"message": "user has been removed from organization"}, status=200)

    else:
        return JsonResponse({"message": "you must be a admin of this org in order to add members"}, status=500)


