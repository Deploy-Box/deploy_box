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
    get_new_user_invite_email_content
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
- Organization projects and resources
- Team collaboration features
- Shared deployments and settings

If you believe this was done in error, please contact your organization administrator 
or reach out to our support team.

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
    subject = f'Departure Confirmation - {organization.name}'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]
    
    # Generate HTML content
    html_content = get_base_email_template(get_left_email_content(user, organization))
    
    # Create plain text fallback
    plain_message = f"""Hello {user.username},

You have successfully left the organization {organization.name}.

Your departure has been processed and you no longer have access to:
- Organization projects and resources
- Team collaboration features
- Shared deployments and settings

Thank you for being part of the team! You can always rejoin if invited again in the future.

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
    subject = f'You\'re Invited to Join {organization.name} on DeployBox! 🚀'
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