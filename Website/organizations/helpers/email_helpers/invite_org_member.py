from django.core.mail import send_mail
from django.core.mail import EmailMessage
from core import settings
from django.contrib.sites.shortcuts import get_current_site
from organizations.models import Organization
from accounts.models import UserProfile
from .email_templates import (
    get_base_email_template,
    get_invite_email_content,
    get_removed_email_content,
    get_left_email_content,
    get_permission_update_email_content,
    get_new_user_invite_email_content,
    get_project_transfer_invitation_content,
    get_project_transfer_accepted_content,
    get_project_transfer_notification_content,
    get_project_transfer_with_signup_invitation_content
)
from organizations.models import PendingInvites

def send_invite_email(user, organization):
    subject = f'Welcome to {organization.name} on DeployBox! 🎉'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]
    
    # Generate HTML content
    html_content = get_base_email_template(get_invite_email_content(user, organization))
    
    # Create plain text fallback
    plain_message = f"""Hello {user.username},

You have been invited to join the organization {organization.name} on DeployBox!

This means you now have access to:
- Collaborate on projects with your team
- Deploy applications together
- Manage shared resources
- Access organization-wide settings

We're excited to have you on board! If you have any questions about your new role, 
don't hesitate to reach out to your organization administrator.

Best regards,
The DeployBox Team"""

    # Send HTML email with plain text fallback
    email_message = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=from_email,
        to=recipient_list
    )
    email_message.content_subtype = "html"
    email_message.send()

def send_user_removed_email(user, organization):
    subject = f'Access Update - {organization.name}'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]
    
    # Generate HTML content
    html_content = get_base_email_template(get_removed_email_content(user, organization))
    
    # Create plain text fallback
    plain_message = f"""Hello {user.username},

Your access to the organization {organization.name} has been removed.

This means you no longer have access to:
- Projects within this organization
- Organization resources and settings
- Team collaboration features

If you believe this was done in error, please contact your organization administrator.

Best regards,
The DeployBox Team"""

    # Send HTML email with plain text fallback
    email_message = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=from_email,
        to=recipient_list
    )
    email_message.content_subtype = "html"
    email_message.send()

def send_user_left_email(user, organization):
    subject = f'Member Left Organization - {organization.name}'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]
    
    # Generate HTML content
    html_content = get_base_email_template(get_left_email_content(user, organization))
    
    # Create plain text fallback
    plain_message = f"""Hello {user.username},

You have successfully left the organization {organization.name}.

You no longer have access to:
- Projects within this organization
- Organization resources and settings
- Team collaboration features

If you need to rejoin this organization, please contact an administrator.

Best regards,
The DeployBox Team"""

    # Send HTML email with plain text fallback
    email_message = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=from_email,
        to=recipient_list
    )
    email_message.content_subtype = "html"
    email_message.send()

def send_user_permission_update_email(user, organization):
    subject = f'Permission Update - {organization.name}'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]
    
    # Generate HTML content
    html_content = get_base_email_template(get_permission_update_email_content(user, organization))
    
    # Create plain text fallback
    plain_message = f"""Hello {user.username},

Your permissions have been updated for the organization {organization.name}.

This change may affect your ability to:
- Access certain projects or resources
- Perform specific actions within the organization
- View or modify organization settings

If you have any questions about your new permissions, please contact your organization administrator.

Best regards,
The DeployBox Team"""

    # Send HTML email with plain text fallback
    email_message = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=from_email,
        to=recipient_list
    )
    email_message.content_subtype = "html"
    email_message.send()

def send_invite_new_user_to_org(user: UserProfile, organization: Organization, email: str):
    subject = f'You\'re Invited to {organization.name} on DeployBox! 🚀'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]
    
    # Get the pending invite to include the invite ID
    try:
        pending_invite = PendingInvites.objects.get(organization=organization, email=email)
        signup_url = f"{settings.HOST}/signup/?invite={pending_invite.id}"
    except PendingInvites.DoesNotExist:
        # Fallback to regular signup URL if invite not found
        signup_url = f"{settings.HOST}/signup"
    
    # Generate HTML content
    html_content = get_base_email_template(get_new_user_invite_email_content(user, organization, signup_url))
    
    # Create plain text fallback
    plain_message = f"""Hello there!

{user.username} has invited you to create an account and join their organization {organization.name} on DeployBox!

DeployBox is a powerful platform for:
- 🚀 Deploying applications with ease
- 👥 Collaborating with your team
- ⚡ Managing infrastructure efficiently
- 🔧 Streamlining your development workflow

Create your account here: {signup_url}

Once you create your account, you'll have immediate access to the organization and can start collaborating right away!

Best regards,
The DeployBox Team"""

    # Send HTML email with plain text fallback
    email_message = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=from_email,
        to=recipient_list
    )
    email_message.content_subtype = "html"
    email_message.send()

def send_project_transfer_invitation(transfer_invitation):
    """Send project transfer invitation email to client"""
    subject = f'Project Ownership Transfer - {transfer_invitation.project.name} 🎯'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [transfer_invitation.to_email]
    
    # Generate accept URL
    accept_url = f"{settings.HOST}/project-transfer/accept/{transfer_invitation.id}"
    
    # Generate HTML content
    html_content = get_base_email_template(get_project_transfer_invitation_content(transfer_invitation, accept_url))
    
    # Create plain text fallback
    plain_message = f"""Hello {transfer_invitation.to_name},

Your developer has built a project on DeployBox and is ready to transfer ownership to you!

Project Details:
- Project Name: {transfer_invitation.project.name}
- Description: {transfer_invitation.project.description}
- Developer: {transfer_invitation.from_organization.name}
{f"- Your Company: {transfer_invitation.to_company}" if transfer_invitation.to_company else ""}

What happens when you accept:
✅ Project ownership transfers to your account
✅ Billing responsibility moves to you
✅ Full control over the project and infrastructure
✅ Developer can remain as collaborator (if you choose)

This invitation expires in 7 days. Accept here: {accept_url}

Best regards,
The DeployBox Team"""

    # Send HTML email with plain text fallback
    email_message = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=from_email,
        to=recipient_list
    )
    email_message.content_subtype = "html"
    email_message.send()

def send_project_transfer_accepted_notification(transfer_invitation):
    """Send confirmation email to client after transfer acceptance"""
    subject = f'Project Transfer Complete - {transfer_invitation.project.name} ✅'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [transfer_invitation.to_email]
    
    # Generate HTML content
    html_content = get_base_email_template(get_project_transfer_accepted_content(transfer_invitation))
    
    # Create plain text fallback
    plain_message = f"""Hello {transfer_invitation.to_name},

Congratulations! You have successfully taken ownership of the project {transfer_invitation.project.name}.

What's been transferred:
✅ Project ownership and control
✅ Billing responsibility
✅ Infrastructure management
✅ All project resources and settings

Next steps:
- Set up your payment method in the dashboard
- Review your project settings and configuration
- Configure any additional team members if needed
- Monitor your usage and billing

You can now access your project from your DeployBox dashboard.

Best regards,
The DeployBox Team"""

    # Send HTML email with plain text fallback
    email_message = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=from_email,
        to=recipient_list
    )
    email_message.content_subtype = "html"
    email_message.send()

def send_project_transfer_completion_notification(transfer_invitation):
    """Send notification to original developer about transfer completion"""
    from .email_templates import get_project_transfer_notification_content
    
    subject = f"Project Transfer Completed: {transfer_invitation.project.name}"
    from_email = settings.EMAIL_HOST_USER
    
    # Get the original developer's email (from the organization)
    developer_email = transfer_invitation.from_organization.email
    recipient_list = [developer_email]
    
    # Generate HTML content
    html_content = get_base_email_template(get_project_transfer_notification_content(transfer_invitation))
    
    # Create plain text fallback
    transfer_date = transfer_invitation.accepted_at.strftime('%B %d, %Y') if transfer_invitation.accepted_at else 'N/A'
    developer_access = 'Maintained' if transfer_invitation.keep_developer else 'Removed'
    
    plain_message = f"""Hello,

The project {transfer_invitation.project.name} has been successfully transferred to {transfer_invitation.to_name}.

Transfer Details:
- New Owner: {transfer_invitation.to_name} ({transfer_invitation.to_email})
- Project: {transfer_invitation.project.name}
- Transfer Date: {transfer_date}
- Developer Access: {developer_access}

The client now has full control over the project and billing. You can continue to collaborate on the project if you were kept as a team member.

Best regards,
The DeployBox Team"""

    # Send HTML email with plain text fallback
    email_message = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=from_email,
        to=recipient_list
    )
    email_message.content_subtype = "html"
    email_message.send()

def send_project_transfer_with_signup_invitation(transfer_invitation, pending_invite):
    """Send project transfer invitation that includes signup for new users"""
    from .email_templates import get_project_transfer_with_signup_invitation_content
    
    subject = f"🎉 Your Project is Ready: {transfer_invitation.project.name}"
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [transfer_invitation.to_email]
    
    # Generate signup URL
    signup_url = f"{settings.HOST}/signup/?invite_id={pending_invite.id}&transfer_id={transfer_invitation.id}"
    
    # Generate HTML content
    html_content = get_base_email_template(get_project_transfer_with_signup_invitation_content(transfer_invitation, pending_invite))
    
    # Create plain text fallback
    plain_message = f"""Hello {transfer_invitation.to_name},

🎉 Your Project is Ready!

Your developer has completed your project on DeployBox and is ready to transfer ownership to you!

Project Details:
- Project Name: {transfer_invitation.project.name}
- Description: {transfer_invitation.project.description}
- Developer: {transfer_invitation.from_organization.name}
{f"- Your Company: {transfer_invitation.to_company}" if transfer_invitation.to_company else ""}

What You'll Get:
✅ Full ownership of your project
✅ Complete control over infrastructure
✅ Billing management
✅ Developer support {'(optional)' if transfer_invitation.keep_developer else ''}
✅ Professional hosting and deployment

Get Started in 2 Steps:
1. Create your DeployBox account (takes 2 minutes)
2. Accept project ownership and start managing your infrastructure

This invitation expires on {transfer_invitation.expires_at.strftime('%B %d, %Y')}.

Create your account and accept the project here: {signup_url}

This link will create your account and automatically accept the project transfer.

If you have any questions, please contact your developer or our support team.

Welcome to DeployBox! 🎉

Best regards,
The DeployBox Team"""

    # Send HTML email with plain text fallback
    email_message = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=from_email,
        to=recipient_list
    )
    email_message.content_subtype = "html"
    email_message.send()