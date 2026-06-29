"""
Organizations service layer — business logic for org management, membership, and transfers.

Returns plain data (dicts, model instances) or raises ServiceError exceptions.
Never imports Response, JsonResponse, or HttpResponse.
"""
import logging
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from typing import Union

from projects.services import create_project
from accounts.models import UserProfile
from organizations.models import Organization, OrganizationMember, PendingInvites, ProjectTransferInvitation, ProjectTransferAudit
from projects.models import Project, ProjectMember
from payments.models import Invoice
from payments.services import create_stripe_customer
from .helpers.email_helpers import invite_org_member
from .helpers import check_permission

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
    from payments.services import create_stripe_customer

    if Organization.has_reached_free_org_limit(user):
        return {
            "error": "Free plan is limited to 1 organization. "
                     "Please upgrade an existing organization to create another."
        }

    try:
        with transaction.atomic():
            stripe_customer_id = create_stripe_customer(name=name, email=email)

            organization = Organization.objects.create(
                            name=name, email=email, stripe_customer_id=stripe_customer_id
                        )
            OrganizationMember.objects.create(user=user, organization=organization, role="admin")

            create_project(
                name="Welcome Project",
                organization_id=organization.id,
                user=user,
                description="This is a welcome project created to get you started.",
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


def update_organization(user: UserProfile, organization_id: str, data: dict) -> dict:
    
    try:
        organization = check_permission.check_permisssion(user, organization_id, requeired_role="admin")
    except check_permission.OrganizationPermissionsError as e:
        raise ForbiddenError(e.message)

    organization.name = data.get("name", organization.name)
    organization.email = data.get("email", organization.email)
    organization.save()

    return {"message": "Organization updated successfully"}


def delete_organization(user: UserProfile, organization_id: str) -> dict:
    organization = get_object_or_404(Organization, id=organization_id)

    if not OrganizationMember.objects.filter(user=user, organization=organization, role="admin").exists():
        raise ForbiddenError("You are not authorized to delete this organization")

    project_count = Project.objects.filter(organization=organization).count()
    if project_count > 0:
        raise ServiceError(
            "Cannot delete organization with active projects. "
            "Please delete or transfer all projects first."
        )

    pending_invoice_count = Invoice.objects.filter(organization=organization, status__in=["draft", "open"]).count()
    if pending_invoice_count > 0:
        raise ServiceError(
            "Cannot delete organization with pending invoices. "
            "Please resolve all outstanding invoices first."
        )

    organization.delete()
    return {"message": "organization deleted"}

def update_user(user: UserProfile, organization: object, user_id: str) -> dict:
    permission_check = OrganizationMember.objects.filter(user=user, organization=organization, role="admin").exists()
    multiple_admin_check = OrganizationMember.objects.filter(organization=organization, role="admin")

    if not permission_check:
        raise ForbiddenError("you must be an admin of this org to update permissions")

    if len(multiple_admin_check) <= 1 and str(user.id) == str(user_id):
        raise ServiceError("in order to downgrade your own permissions there must be more than one admin")

    org_user = UserProfile.objects.get(id=user_id)
    org_member = OrganizationMember.objects.get(organization=organization, user=org_user)

    if org_member.role.lower() == "admin":
        org_member.role = "member"
    else:
        org_member.role = "admin"
    org_member.save()
    invite_org_member.send_user_permission_update_email(user=org_user, organization=organization)
    return {"message": "user permission updated successfully"}


def add_org_member(user: UserProfile, organization_id: str, member: str, role: str) -> dict:
    try:
        organization = check_permission.check_permisssion(user, organization_id, requeired_role="admin")
    except check_permission.OrganizationPermissionsError as e:
        raise ForbiddenError(e.message)

    try:
        member_user = UserProfile.objects.get(username=member)
    except UserProfile.DoesNotExist:
        raise NotFoundError("User not found")

    if OrganizationMember.objects.filter(organization=organization, user=member_user).exists():
        raise ServiceError("User is already a member of this organization")

    OrganizationMember.objects.create(user=member_user, organization=organization, role=role)
    return {"message": "Member added successfully"}


def remove_org_member(user: UserProfile, organization_id: str, user_id: str) -> dict:
    try:
        organization = check_permission.check_permisssion(user, organization_id, requeired_role="admin")
    except check_permission.OrganizationPermissionsError as e:
        raise ForbiddenError(e.message)

    try:
        member_user = UserProfile.objects.get(id=user_id)
    except UserProfile.DoesNotExist:
        raise NotFoundError("User not found")

    organization_member = OrganizationMember.objects.filter(organization=organization, user=member_user).first()
    if not organization_member:
        raise NotFoundError("User is not a member of this organization")

    if organization_member.user == user:
        raise ServiceError("You cannot remove yourself from the organization")

    organization_member.delete()
    return {"message": "Member removed successfully"}


def leave_organization(user: UserProfile, organization_id: str) -> dict:
    try:
        organization = check_permission.check_permisssion(user, organization_id, requeired_role="member")
    except check_permission.OrganizationPermissionsError as e:
        raise ForbiddenError(e.message)

    organization_member = OrganizationMember.objects.filter(organization=organization, user=user).first()
    if not organization_member:
        raise NotFoundError("You are not a member of this organization")

    organization_member.delete()
    return {"message": "You have successfully left the organization"}


def invite_new_user_to_org(user: UserProfile, organization: Organization, email: str) -> dict:
    PendingInvites.objects.get_or_create(
        organization=organization,
        email=email
    )
    invite_org_member.send_invite_new_user_to_org(user, organization, email)
    return {"message": "invite email has been sent to user"}


def remove_pending_invite(user: UserProfile, organization_id: str, invite_id: str) -> dict:
    try:
        organization = check_permission.check_permisssion(user, organization_id, requeired_role="admin")
    except check_permission.OrganizationPermissionsError as e:
        raise ForbiddenError(e.message)

    try:
        pending_invite = PendingInvites.objects.get(id=invite_id, organization=organization)
    except PendingInvites.DoesNotExist:
        raise NotFoundError("Pending invite not found")

    pending_invite.delete()
    return {"message": "Pending invite removed successfully", "success": True}

def initiate_project_transfer(user: UserProfile, project_id: str, client_email: str, client_name: str, client_company: str = None, keep_developer: bool = True) -> dict:
    """Initiate a project ownership transfer to a client."""
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        raise NotFoundError("Project not found")

    project_member = ProjectMember.objects.filter(
        project=project, user=user, role="admin"
    ).first()
    if not project_member:
        raise ForbiddenError("You don't have permission to transfer this project")

    existing_transfer = ProjectTransferInvitation.objects.filter(
        project=project, status="pending"
    ).first()
    if existing_transfer:
        raise ServiceError("There's already a pending transfer for this project")

    expires_at = timezone.now() + timedelta(days=7)

    transfer_invitation = ProjectTransferInvitation.objects.create(
        project=project,
        from_organization=project.organization,
        to_email=client_email,
        to_name=client_name,
        to_company=client_company,
        keep_developer=keep_developer,
        expires_at=expires_at,
    )

    ProjectTransferAudit.objects.create(
        transfer_invitation=transfer_invitation,
        action="initiated",
        details=f"Transfer initiated by {user.username} to {client_email}",
        performed_by=user,
    )

    client_user_exists = UserProfile.objects.filter(email=client_email).exists()

    if client_user_exists:
        invite_org_member.send_project_transfer_invitation(transfer_invitation)
    else:
        pending_invite, created = PendingInvites.objects.get_or_create(
            organization=project.organization,
            email=client_email,
        )
        invite_org_member.send_project_transfer_with_signup_invitation(transfer_invitation, pending_invite)

    return {
        "message": "Project transfer invitation sent successfully",
        "transfer_id": str(transfer_invitation.id),
        "client_has_account": client_user_exists,
    }

def accept_project_transfer(transfer_id: str, client_user: UserProfile) -> dict:
    """Accept a project ownership transfer."""
    try:
        transfer_invitation = ProjectTransferInvitation.objects.get(id=transfer_id, status="pending")
    except ProjectTransferInvitation.DoesNotExist:
        raise NotFoundError("Transfer invitation not found")

    if transfer_invitation.is_expired():
        transfer_invitation.status = "expired"
        transfer_invitation.save()
        ProjectTransferAudit.objects.create(
            transfer_invitation=transfer_invitation,
            action="expired",
            details="Transfer expired before acceptance",
            performed_by=client_user,
        )
        raise ServiceError("Transfer invitation has expired")

    # Get or create client organization
    client_organization = None
    existing_membership = OrganizationMember.objects.filter(user=client_user).first()

    if existing_membership:
        client_organization = existing_membership.organization
    elif hasattr(client_user, 'organization'):
        client_organization = client_user.organization
    else:
        from payments.services import create_stripe_customer
        stripe_customer_id = create_stripe_customer(name=client_user.username, email=client_user.email)
        client_organization = Organization.objects.create(
            name=f"{client_user.username}'s Organization",
            email=client_user.email,
            stripe_customer_id=stripe_customer_id,
        )
        OrganizationMember.objects.create(
            user=client_user,
            organization=client_organization,
            role="admin",
        )

    with transaction.atomic():
        transfer_invitation.status = "accepted"
        transfer_invitation.accepted_at = timezone.now()
        transfer_invitation.to_organization = client_organization
        transfer_invitation.save()

        project = transfer_invitation.project
        project.organization = client_organization
        project.save()

        if transfer_invitation.keep_developer:
            ProjectMember.objects.get_or_create(
                user=client_user,
                project=project,
                defaults={'role': 'admin'},
            )
        else:
            ProjectMember.objects.filter(project=project).delete()
            ProjectMember.objects.create(
                user=client_user,
                project=project,
                role="admin",
            )

        ProjectTransferAudit.objects.create(
            transfer_invitation=transfer_invitation,
            action="accepted",
            details=f"Transfer accepted by {client_user.username}",
            performed_by=client_user,
        )
        ProjectTransferAudit.objects.create(
            transfer_invitation=transfer_invitation,
            action="billing_transferred",
            details=f"Billing responsibility transferred to {client_organization.name}",
            performed_by=client_user,
        )
        ProjectTransferAudit.objects.create(
            transfer_invitation=transfer_invitation,
            action="infrastructure_transferred",
            details=f"Project infrastructure transferred to {client_organization.name}",
            performed_by=client_user,
        )

    invite_org_member.send_project_transfer_accepted_notification(transfer_invitation)
    invite_org_member.send_project_transfer_completion_notification(transfer_invitation)

    return {
        "message": "Project transfer completed successfully",
        "project_id": str(project.id),
        "organization_id": str(client_organization.id),
    }

def get_project_transfer_status(transfer_id: str) -> dict:
    """Get the status of a project transfer invitation."""
    try:
        transfer_invitation = ProjectTransferInvitation.objects.get(id=transfer_id)
    except ProjectTransferInvitation.DoesNotExist:
        raise NotFoundError("Transfer invitation not found")

    return {
        "transfer_id": str(transfer_invitation.id),
        "project_name": transfer_invitation.project.name,
        "status": transfer_invitation.status,
        "expires_at": transfer_invitation.expires_at.isoformat(),
        "is_expired": transfer_invitation.is_expired(),
        "created_at": transfer_invitation.created_at.isoformat(),
        "accepted_at": transfer_invitation.accepted_at.isoformat() if transfer_invitation.accepted_at else None,
    }


def cancel_project_transfer(user: UserProfile, transfer_id: str) -> dict:
    """Cancel a project transfer invitation."""
    try:
        transfer_invitation = ProjectTransferInvitation.objects.get(id=transfer_id, status="pending")
    except ProjectTransferInvitation.DoesNotExist:
        raise NotFoundError("Transfer invitation not found or already processed")

    project_member = ProjectMember.objects.filter(
        project=transfer_invitation.project, user=user, role="admin"
    ).first()
    if not project_member:
        raise ForbiddenError("You don't have permission to cancel this transfer")

    transfer_invitation.status = "declined"
    transfer_invitation.save()

    ProjectTransferAudit.objects.create(
        transfer_invitation=transfer_invitation,
        action="declined",
        details=f"Transfer cancelled by {user.username}",
        performed_by=user,
    )

    return {"message": "Project transfer invitation cancelled successfully"}


def get_user_transfer_invitations(user: UserProfile) -> dict:
    """Get all transfer invitations for a user."""
    received_transfers = ProjectTransferInvitation.objects.filter(
        to_email=user.email, status="pending"
    ).select_related('project', 'from_organization')

    sent_transfers = ProjectTransferInvitation.objects.filter(
        from_organization__organizationmember__user=user,
        status__in=["pending", "accepted", "declined"],
    ).select_related('project', 'to_organization')

    received_data = [
        {
            "id": str(t.id),
            "project_name": t.project.name,
            "project_description": t.project.description,
            "from_organization": t.from_organization.name,
            "to_name": t.to_name,
            "to_company": t.to_company,
            "keep_developer": t.keep_developer,
            "expires_at": t.expires_at.isoformat(),
            "is_expired": t.is_expired(),
            "created_at": t.created_at.isoformat(),
        }
        for t in received_transfers
    ]

    sent_data = [
        {
            "id": str(t.id),
            "project_name": t.project.name,
            "to_email": t.to_email,
            "to_name": t.to_name,
            "to_company": t.to_company,
            "status": t.status,
            "expires_at": t.expires_at.isoformat(),
            "accepted_at": t.accepted_at.isoformat() if t.accepted_at else None,
            "created_at": t.created_at.isoformat(),
        }
        for t in sent_transfers
    ]

    return {
        "received_transfers": received_data,
        "sent_transfers": sent_data,
    }


def transfer_project_to_organization(user: UserProfile, project_id: str, target_organization_id: str, keep_developer: bool = True) -> dict:
    """Transfer a project to another organization."""
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        raise NotFoundError("Project not found")

    project_member = ProjectMember.objects.filter(
        project=project, user=user, role="admin"
    ).first()
    if not project_member:
        raise ForbiddenError("You don't have permission to transfer this project")

    try:
        target_organization = Organization.objects.get(id=target_organization_id)
    except Organization.DoesNotExist:
        raise NotFoundError("Target organization not found")

    if not OrganizationMember.objects.filter(organization=target_organization, user=user).exists():
        raise ForbiddenError("You must be a member of the target organization")

    if project.organization.id == target_organization_id:
        raise ServiceError("Project is already in the target organization")

    with transaction.atomic():
        project.organization = target_organization
        project.save()

        if not keep_developer:
            ProjectMember.objects.filter(project=project).delete()
            ProjectMember.objects.create(user=user, project=project, role="admin")

    return {"message": f"Project '{project.name}' successfully transferred to '{target_organization.name}'"}