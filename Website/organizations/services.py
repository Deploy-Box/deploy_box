import logging
from django.http import JsonResponse
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from typing import Union

from projects.services import create_project
from accounts.models import UserProfile
from organizations.models import Organization, OrganizationMember, PendingInvites, ProjectTransferInvitation, ProjectTransferAudit
from projects.models import Project, ProjectMember
from payments.services import create_stripe_user
from .helpers.email_helpers import invite_org_member
from .helpers import check_permission

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
    """Get organization if user is a member."""
    organization = Organization.objects.filter(id=organization_id).first()
    organization_member = OrganizationMember.objects.filter(organization=organization, user=user).first()

    if not organization:
        return None

    if not organization_member:
        return None

    return organization


def create_organization(user: UserProfile, name: str, email: str) -> Union[dict, dict]:
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

    return {
        "id": str(organization.id),
        "name": organization.name,
        "email": organization.email,
        "created_at": organization.created_at.isoformat(),
        "message": "Organization created successfully"
    }


def update_organization(user: UserProfile, organization_id: str, data: dict) -> JsonResponse:
    
    try:
        organization = check_permission.check_permisssion(user, organization_id, requeired_role="admin")
    except check_permission.OrganizationPermissionsError as e:
        return e.to_response()

    try:
        organization.name = data.get("name", organization.name)
        organization.email = data.get("email", organization.email)
        organization.save()

        return JsonResponse({"message": "Organization updated successfully"}, status=200)

    except Exception as e:
        return JsonResponse({"message": f"an unexpected error occured: {e}"}, status=400)


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
            invite_org_member.send_user_permission_update_email(user=org_user, organization=organization)
            return JsonResponse({"message": "user permission updated successfully"}, status=200)
        else:
            org_member.role = "admin"
            org_member.save()
            invite_org_member.send_user_permission_update_email(user=org_user, organization=organization)
            return JsonResponse({"message": "user permission updated successfully"}, status=200)

    except Exception as e:
        return JsonResponse({"message": f'an unexpected error occured {e}'}, status=400)


def add_org_member(user: UserProfile, organization_id: str, member: str, role: str) -> JsonResponse:
    try:
        organization = check_permission.check_permisssion(user, organization_id, requeired_role="admin")
    except check_permission.OrganizationPermissionsError as e:
        return e.to_response()

    try:
        member_user = UserProfile.objects.get(username=member)
        organization_member = OrganizationMember.objects.filter(organization=organization, user=member_user).first()

        if organization_member:
            return JsonResponse({"message": "User is already a member of this organization"}, status=400)

        OrganizationMember.objects.create(user=member_user, organization=organization, role=role)

        return JsonResponse({"message": "Member added successfully"}, status=200)

    except UserProfile.DoesNotExist:
        return JsonResponse({"message": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"message": f"an unexpected error occured: {e}"}, status=400)


def remove_org_member(user: UserProfile, organization_id: str, user_id: str) -> JsonResponse:
    try:
        organization = check_permission.check_permisssion(user, organization_id, requeired_role="admin")
    except check_permission.OrganizationPermissionsError as e:
        return e.to_response()

    try:
        member_user = UserProfile.objects.get(id=user_id)
        organization_member = OrganizationMember.objects.filter(organization=organization, user=member_user).first()

        if not organization_member:
            return JsonResponse({"message": "User is not a member of this organization"}, status=404)

        if organization_member.user == user:
            return JsonResponse({"message": "You cannot remove yourself from the organization"}, status=400)

        organization_member.delete()

        return JsonResponse({"message": "Member removed successfully"}, status=200)

    except UserProfile.DoesNotExist:
        return JsonResponse({"message": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"message": f"an unexpected error occured: {e}"}, status=400)


def leave_organization(user: UserProfile, organization_id: str) -> JsonResponse:
    try:
        organization = check_permission.check_permisssion(user, organization_id, requeired_role="member")
    except check_permission.OrganizationPermissionsError as e:
        return e.to_response()

    try:
        organization_member = OrganizationMember.objects.filter(organization=organization, user=user).first()

        if not organization_member:
            return JsonResponse({"message": "You are not a member of this organization"}, status=404)

        organization_member.delete()

        return JsonResponse({"message": "You have successfully left the organization"}, status=200)

    except Exception as e:
        return JsonResponse({
            "message": f"an unexpected error occured: {e}"
        }, status=500)

def invite_new_user_to_org(user: UserProfile, organization: Organization, email: str ):
    try:
        # with transaction.atomic():
            # Use get_or_create to handle unique constraint
            pending_invite, created = PendingInvites.objects.get_or_create(
                organization=organization,
                email=email
            )
            
            invite_org_member.send_invite_new_user_to_org(user, organization, email)
            return JsonResponse({"message": "invite email has been sent to user"}, status=200)
    except Exception as e:
        return JsonResponse({"message": f"an unexpected error occured: {e}"}, status=400)

def remove_pending_invite(user: UserProfile, organization_id: str, invite_id: str) -> JsonResponse:
    try:
        organization = check_permission.check_permisssion(user, organization_id, requeired_role="admin")
    except check_permission.OrganizationPermissionsError as e:
        return e.to_response()

    try:
        pending_invite = PendingInvites.objects.get(id=invite_id, organization=organization)
        pending_invite.delete()

        return JsonResponse({"message": "Pending invite removed successfully", "success": True}, status=200)

    except PendingInvites.DoesNotExist:
        return JsonResponse({"message": "Pending invite not found"}, status=404)
    except Exception as e:
        return JsonResponse({"message": f"an unexpected error occured: {e}"}, status=400)

def initiate_project_transfer(user: UserProfile, project_id: str, client_email: str, client_name: str, client_company: str = None, keep_developer: bool = True) -> JsonResponse:
    """Initiate a project ownership transfer to a client"""
    try:
        # Get the project and check permissions
        project = Project.objects.get(id=project_id)
        project_member = ProjectMember.objects.filter(
            project=project, 
            user=user, 
            role="admin"
        ).first()
        
        if not project_member:
            return JsonResponse({"message": "You don't have permission to transfer this project"}, status=403)
        
        # Check if there's already a pending transfer for this project
        existing_transfer = ProjectTransferInvitation.objects.filter(
            project=project,
            status="pending"
        ).first()
        
        if existing_transfer:
            return JsonResponse({"message": "There's already a pending transfer for this project"}, status=400)
        
        # Set expiration date (7 days from now)
        from django.utils import timezone
        from datetime import timedelta
        expires_at = timezone.now() + timedelta(days=7)
        
        # Create transfer invitation
        transfer_invitation = ProjectTransferInvitation.objects.create(
            project=project,
            from_organization=project.organization,
            to_email=client_email,
            to_name=client_name,
            to_company=client_company,
            keep_developer=keep_developer,
            expires_at=expires_at
        )
        
        # Create audit log
        ProjectTransferAudit.objects.create(
            transfer_invitation=transfer_invitation,
            action="initiated",
            details=f"Transfer initiated by {user.username} to {client_email}",
            performed_by=user
        )
        
        # Check if client already has an account
        client_user_exists = UserProfile.objects.filter(email=client_email).exists()
        
        if client_user_exists:
            # Client has account - send regular transfer invitation
            invite_org_member.send_project_transfer_invitation(transfer_invitation)
        else:
            # Client doesn't have account - create organization invite and send combined invitation
            from organizations.models import PendingInvites
            
            # Use get_or_create to handle unique constraint
            pending_invite, created = PendingInvites.objects.get_or_create(
                organization=project.organization,
                email=client_email
            )
            
            # Send combined invitation email
            invite_org_member.send_project_transfer_with_signup_invitation(transfer_invitation, pending_invite)
        
        return JsonResponse({
            "message": "Project transfer invitation sent successfully",
            "transfer_id": str(transfer_invitation.id),
            "client_has_account": client_user_exists
        }, status=200)
        
    except Project.DoesNotExist:
        return JsonResponse({"message": "Project not found"}, status=404)
    except Exception as e:
        return JsonResponse({"message": f"An unexpected error occurred: {e}"}, status=500)

def accept_project_transfer(transfer_id: str, client_user: UserProfile) -> JsonResponse:
    """Accept a project ownership transfer"""
    try:
        # Get the transfer invitation
        transfer_invitation = ProjectTransferInvitation.objects.get(id=transfer_id, status="pending")
        
        # Check if transfer has expired
        if transfer_invitation.is_expired():
            transfer_invitation.status = "expired"
            transfer_invitation.save()
            
            ProjectTransferAudit.objects.create(
                transfer_invitation=transfer_invitation,
                action="expired",
                details="Transfer expired before acceptance",
                performed_by=client_user
            )
            
            return JsonResponse({"message": "Transfer invitation has expired"}, status=400)
        
        # Get or create client organization
        client_organization = None
        
        # Check if user is already a member of any organization
        existing_membership = OrganizationMember.objects.filter(user=client_user).first()
        
        if existing_membership:
            # User is already a member of an organization, use that one
            client_organization = existing_membership.organization
        elif hasattr(client_user, 'organization'):
            # Fallback to the old logic (though this shouldn't happen)
            client_organization = client_user.organization
        else:
            # Create new organization for client
            from payments.services import create_stripe_user
            stripe_customer_id = create_stripe_user(name=client_user.username, email=client_user.email)
            client_organization = Organization.objects.create(
                name=f"{client_user.username}'s Organization",
                email=client_user.email,
                stripe_customer_id=stripe_customer_id
            )
            OrganizationMember.objects.create(
                user=client_user,
                organization=client_organization,
                role="admin"
            )
        
        with transaction.atomic():
            # Update transfer invitation
            transfer_invitation.status = "accepted"
            transfer_invitation.accepted_at = timezone.now()
            transfer_invitation.to_organization = client_organization
            transfer_invitation.save()
            
            # Transfer project ownership
            project = transfer_invitation.project
            project.organization = client_organization
            project.save()
            
            # Transfer project members if keeping developer
            if transfer_invitation.keep_developer:
                # Add client as admin to the project
                ProjectMember.objects.get_or_create(
                    user=client_user,
                    project=project,
                    defaults={'role': 'admin'}
                )
                
                # Keep existing project members
                pass
            else:
                # Remove all existing project members and add client as admin
                ProjectMember.objects.filter(project=project).delete()
                ProjectMember.objects.create(
                    user=client_user,
                    project=project,
                    role="admin"
                )
            
            # Create audit logs
            ProjectTransferAudit.objects.create(
                transfer_invitation=transfer_invitation,
                action="accepted",
                details=f"Transfer accepted by {client_user.username}",
                performed_by=client_user
            )
            
            ProjectTransferAudit.objects.create(
                transfer_invitation=transfer_invitation,
                action="billing_transferred",
                details=f"Billing responsibility transferred to {client_organization.name}",
                performed_by=client_user
            )
            
            ProjectTransferAudit.objects.create(
                transfer_invitation=transfer_invitation,
                action="infrastructure_transferred",
                details=f"Project infrastructure transferred to {client_organization.name}",
                performed_by=client_user
            )
        
        # Send confirmation emails
        invite_org_member.send_project_transfer_accepted_notification(transfer_invitation)
        invite_org_member.send_project_transfer_completion_notification(transfer_invitation)
        
        return JsonResponse({
            "message": "Project transfer completed successfully",
            "project_id": str(project.id),
            "organization_id": str(client_organization.id)
        }, status=200)
        
    except ProjectTransferInvitation.DoesNotExist:
        return JsonResponse({"message": "Transfer invitation not found"}, status=404)
    except Exception as e:
        return JsonResponse({"message": f"An unexpected error occurred: {e}"}, status=500)

def get_project_transfer_status(transfer_id: str) -> JsonResponse:
    """Get the status of a project transfer invitation"""
    try:
        transfer_invitation = ProjectTransferInvitation.objects.get(id=transfer_id)
        
        return JsonResponse({
            "transfer_id": str(transfer_invitation.id),
            "project_name": transfer_invitation.project.name,
            "status": transfer_invitation.status,
            "expires_at": transfer_invitation.expires_at.isoformat(),
            "is_expired": transfer_invitation.is_expired(),
            "created_at": transfer_invitation.created_at.isoformat(),
            "accepted_at": transfer_invitation.accepted_at.isoformat() if transfer_invitation.accepted_at else None
        }, status=200)
        
    except ProjectTransferInvitation.DoesNotExist:
        return JsonResponse({"message": "Transfer invitation not found"}, status=404)
    except Exception as e:
        return JsonResponse({"message": f"An unexpected error occurred: {e}"}, status=500)

def cancel_project_transfer(user: UserProfile, transfer_id: str) -> JsonResponse:
    """Cancel a project transfer invitation"""
    try:
        # Get the transfer invitation
        transfer_invitation = ProjectTransferInvitation.objects.get(id=transfer_id, status="pending")
        
        # Check if user has permission to cancel (must be admin of the project)
        project_member = ProjectMember.objects.filter(
            project=transfer_invitation.project, 
            user=user, 
            role="admin"
        ).first()
        
        if not project_member:
            return JsonResponse({"message": "You don't have permission to cancel this transfer"}, status=403)
        
        # Update transfer status
        transfer_invitation.status = "declined"
        transfer_invitation.save()
        
        # Create audit log
        ProjectTransferAudit.objects.create(
            transfer_invitation=transfer_invitation,
            action="declined",
            details=f"Transfer cancelled by {user.username}",
            performed_by=user
        )
        
        return JsonResponse({
            "message": "Project transfer invitation cancelled successfully"
        }, status=200)
        
    except ProjectTransferInvitation.DoesNotExist:
        return JsonResponse({"message": "Transfer invitation not found or already processed"}, status=404)
    except Exception as e:
        return JsonResponse({"message": f"An unexpected error occurred: {e}"}, status=500)

def get_user_transfer_invitations(user: UserProfile) -> JsonResponse:
    """Get all transfer invitations for a user"""
    try:
        # Get transfers where user is the recipient
        received_transfers = ProjectTransferInvitation.objects.filter(
            to_email=user.email,
            status="pending"
        ).select_related('project', 'from_organization')
        
        # Get transfers initiated by user's organizations
        sent_transfers = ProjectTransferInvitation.objects.filter(
            from_organization__organizationmember__user=user,
            status__in=["pending", "accepted", "declined"]
        ).select_related('project', 'to_organization')
        
        received_data = []
        for transfer in received_transfers:
            received_data.append({
                "id": str(transfer.id),
                "project_name": transfer.project.name,
                "project_description": transfer.project.description,
                "from_organization": transfer.from_organization.name,
                "to_name": transfer.to_name,
                "to_company": transfer.to_company,
                "keep_developer": transfer.keep_developer,
                "expires_at": transfer.expires_at.isoformat(),
                "is_expired": transfer.is_expired(),
                "created_at": transfer.created_at.isoformat()
            })
        
        sent_data = []
        for transfer in sent_transfers:
            sent_data.append({
                "id": str(transfer.id),
                "project_name": transfer.project.name,
                "to_email": transfer.to_email,
                "to_name": transfer.to_name,
                "to_company": transfer.to_company,
                "status": transfer.status,
                "expires_at": transfer.expires_at.isoformat(),
                "accepted_at": transfer.accepted_at.isoformat() if transfer.accepted_at else None,
                "created_at": transfer.created_at.isoformat()
            })
        
        return JsonResponse({
            "received_transfers": received_data,
            "sent_transfers": sent_data
        }, status=200)
        
    except Exception as e:
        return JsonResponse({"message": f"An unexpected error occurred: {e}"}, status=500)

def transfer_project_to_organization(user: UserProfile, project_id: str, target_organization_id: str, keep_developer: bool = True) -> JsonResponse:
    """Transfer a project to another organization"""
    try:
        # Get the project and check permissions
        project = Project.objects.get(id=project_id)
        project_member = ProjectMember.objects.filter(
            project=project, 
            user=user, 
            role="admin"
        ).first()
        
        if not project_member:
            return JsonResponse({"message": "You don't have permission to transfer this project"}, status=403)
        
        # Get the target organization and check if user is a member
        target_organization = Organization.objects.get(id=target_organization_id)
        target_org_member = OrganizationMember.objects.filter(
            organization=target_organization,
            user=user
        ).first()
        
        if not target_org_member:
            return JsonResponse({"message": "You must be a member of the target organization"}, status=403)
        
        # Check if project is already in the target organization
        if project.organization.id == target_organization_id:
            return JsonResponse({"message": "Project is already in the target organization"}, status=400)
        
        # Transfer the project
        with transaction.atomic():
            # Update project organization
            project.organization = target_organization
            project.save()
            
            # Handle project members based on keep_developer setting
            if keep_developer:
                # Keep existing project members
                pass
            else:
                # Remove all existing project members and add user as admin
                ProjectMember.objects.filter(project=project).delete()
                ProjectMember.objects.create(
                    user=user,
                    project=project,
                    role="admin"
                )
            
            # Note: We can't create an audit log for direct transfers since ProjectTransferAudit requires a transfer_invitation
            # This is a limitation of the current model design
            pass
        
        return JsonResponse({
            "message": f"Project '{project.name}' successfully transferred to '{target_organization.name}'"
        }, status=200)
        
    except Project.DoesNotExist:
        return JsonResponse({"message": "Project not found"}, status=404)
    except Organization.DoesNotExist:
        return JsonResponse({"message": "Target organization not found"}, status=404)
    except Exception as e:
        return JsonResponse({"message": f"An unexpected error occurred: {e}"}, status=500)


