import logging
from django.http import JsonResponse
from django.db import transaction
from django.shortcuts import get_object_or_404
from typing import Union

from projects.services import create_project
from accounts.models import UserProfile
from organizations.models import Organization, OrganizationMember, PendingInvites
from .helpers.email_helpers import invite_org_member

logger = logging.getLogger(__name__)


def get_organizations(user: UserProfile) -> list[Organization]:
    """
    Get organizations for a user.
    """
    if not user.pk:
        raise ValueError("The user instance must be saved before querying related filters.")
    organizations = Organization.objects.filter(organizationmember__user=user).distinct()
    if not organizations.exists():
        return []

    return list(organizations)

def get_organization(user: UserProfile, organization_id: str) -> Union[Organization, None]:
    """
    Get organization for a user.
    """
    organization = Organization.objects.filter(organizationmember__user=user, id=organization_id).first()

    if not organization:
        return None

    return organization


def create_organization(user: UserProfile, name: str, email: str) -> Union[Organization, dict]:
    from payments.services import create_stripe_user

    try:
        with transaction.atomic():
            stripe_customer_id = create_stripe_user(name=name, email=email)

            organization = Organization.objects.create(
                            name=name, email=email, stripe_customer_id=stripe_customer_id
                        )
            OrganizationMember.objects.create(user=user, organization=organization, role="admin")

            create_project(
                name="Default Project",
                organization_id=organization.id,
                user=user,
                description="This is the default project created for you.",
            )

    except Exception as e:
        return {"error": str(e)}

    return organization


def update_organization(user: UserProfile, organization_id: str, data: dict) -> JsonResponse:
    organization = get_object_or_404(Organization, id=organization_id)

    # Check if the user is an admin of the organization
    if not OrganizationMember.objects.filter(user=user, organization=organization, role="admin").exists():
        return JsonResponse({"error": "You are not authorized to update this organization", "success": False}, status=403)

    organization.name = data.get("name", organization.name)
    organization.email = data.get("email", organization.email)
    organization.stripe_customer_id = data.get("stripe_customer_id", organization.stripe_customer_id)
    organization.save()

    return JsonResponse({
        "id": organization.id,
        "name": organization.name,
        "email": organization.email,
        "success": True,
    }, status=200)


def delete_organization(user: UserProfile, organization_id: str) -> JsonResponse:
    organization = get_object_or_404(Organization, id=organization_id)

    # Check if the user is an admin of the organization
    if not OrganizationMember.objects.filter(user=user, organization=organization, role="admin").exists():
        return JsonResponse({"error": "You are not authorized to delete this organization"}, status=403)

    # TODO: Check if the organization has any projects

    organization.delete()

    return JsonResponse({"message": "organization deleted"}, status=200)

def update_user(user: UserProfile, organization: object, user_id: str) -> JsonResponse:
    permission_check = OrganizationMember.objects.filter(user=user, organization=organization, role="admin").exists()
    multiple_admin_check = OrganizationMember.objects.filter(organization=organization, role="admin")

    if not permission_check:
        return JsonResponse({"message": "you must be an admin of this org to update permissions"}, status=400)

    if len(multiple_admin_check) <= 1 and user.id == int(user_id): # type: ignore
        return JsonResponse({"message": "in order to downgrade your own permissions there must be more than one admin"}, status=400)

    try:
        org_user = UserProfile.objects.get(id=user_id)
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


def add_org_members(member: str, role: str, organization: object, user: UserProfile) -> JsonResponse:
    permission_check = OrganizationMember.objects.filter(user_id=user, organization=organization, role='admin').exists()

    if permission_check:
        user_to_add = UserProfile.objects.get(username=member)

        if not user_to_add:
            return JsonResponse({"message": "user could not be found please ensuer username is correct"}, status=404)

        member_check = OrganizationMember.objects.filter(organization=organization, user=user_to_add)

        if member_check:
            return JsonResponse({"message": "this user is already a member of this organization"}, status=200)

        OrganizationMember.objects.create(organization=organization, user=user_to_add, role=role.lower())

        invite_org_member.send_invite_email(user_to_add, organization)

        return JsonResponse({"message": "user has been successfully added"}, status=200)

    else:
        return JsonResponse({"message": "you must be a admin of this org in order to add members"}, status=500)

def remove_org_member(user: UserProfile, organization_id: str, member_id: str) -> JsonResponse:
    """
    Remove a member from an organization. Only admins can remove members.
    """
    try:
        organization = Organization.objects.get(id=organization_id)
        
        # Check if the user is an admin of this organization
        is_admin = OrganizationMember.objects.filter(
            user=user, 
            organization=organization, 
            role='admin'
        ).exists()
        
        if not is_admin:
            return JsonResponse({
                "message": "You must be an admin of this organization to remove members"
            }, status=403)
        
        # Get the member to remove
        member_to_remove = OrganizationMember.objects.filter(
            id=member_id, 
            organization=organization
        ).first()
        
        if not member_to_remove:
            return JsonResponse({
                "message": "Member not found in this organization"
            }, status=404)
        
        # Check if trying to remove the last admin
        admin_count = OrganizationMember.objects.filter(
            organization=organization, 
            role='admin'
        ).count()
        
        if member_to_remove.role == 'admin' and admin_count <= 1:
            return JsonResponse({
                "message": "Cannot remove the last admin from the organization"
            }, status=400)
        
        # Send email notification
        invite_org_member.send_user_removed_email(member_to_remove.user, organization)
        
        # Remove the member
        member_to_remove.delete()
        
        return JsonResponse({
            "message": "Member has been removed from the organization"
        }, status=200)
        
    except Organization.DoesNotExist:
        return JsonResponse({
            "message": "Organization not found"
        }, status=404)
    except Exception as e:
        logger.error(f"Error removing member: {e}")
        return JsonResponse({
            "message": "An unexpected error occurred"
        }, status=500)

def leave_organization(user: UserProfile, organization_id: str) -> JsonResponse:
    """
    Allow a user to leave an organization themselves.
    """
    try:
        organization = Organization.objects.get(id=organization_id)
        
        # Get the user's membership
        user_membership = OrganizationMember.objects.filter(
            user=user, 
            organization=organization
        ).first()
        
        if not user_membership:
            return JsonResponse({
                "message": "You are not a member of this organization"
            }, status=404)
        
        # Check if this is the last admin
        if user_membership.role == 'admin':
            admin_count = OrganizationMember.objects.filter(
                organization=organization, 
                role='admin'
            ).count()
            
            if admin_count <= 1:
                return JsonResponse({
                    "message": "Cannot leave organization as the last admin. Please transfer admin role or delete the organization."
                }, status=400)
        
        # Send email notification
        invite_org_member.send_user_left_email(user, organization)
        
        # Remove the user's membership
        user_membership.delete()
        
        return JsonResponse({
            "message": "You have successfully left the organization"
        }, status=200)
        
    except Organization.DoesNotExist:
        return JsonResponse({
            "message": "Organization not found"
        }, status=404)
    except Exception as e:
        logger.error(f"Error leaving organization: {e}")
        return JsonResponse({
            "message": "An unexpected error occurred"
        }, status=500)

def invite_new_user_to_org(user: UserProfile, organization: Organization, email: str ):
    try:
        invite_org_member.send_invite_new_user_to_org(user, organization, email)
        PendingInvites.objects.create(organization=organization, email=email)
        return JsonResponse({"message": "invite email has been sent to user"}, status=200)
    except Exception as e:
        return JsonResponse({"message": f"an unexpected error occured: {e}"}, status=400)


