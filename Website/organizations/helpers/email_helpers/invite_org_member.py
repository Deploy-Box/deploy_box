from django.core.mail import send_mail
from core import settings
from django.contrib.sites.shortcuts import get_current_site
from organizations.models import Organization
from accounts.models import User

def send_invite_email(user, organization):
    subject = 'You have been invited to join an organization'
    message = f"Hello {user.username},\n\nYou have been add to {organization.name}.\n\nBest regards,\nThe Team"
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]

    send_mail(subject, message, from_email, recipient_list)

def send_user_removed_email(user, organization):
    subject = 'You have been removed from an organization'
    message = f"Hello {user.username},\n\nYou have been removed from {organization.name}.\n\nBest regards,\nThe Team"
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]

    send_mail(subject, message, from_email, recipient_list)

def send_user_permission_update_emaill(user, organization):
    subject = 'Your permissions have been updated for an organization'
    message = f"Hello {user.username},\n\nYour permissions have been updated for {organization.name}.\n\nBest regards,\nThe Team"
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]

    send_mail(subject, message, from_email, recipient_list)

def send_invite_new_user_to_org(user: User, organization: Organization, email: str):
    subject = f'You have been invited to join {organization.name} on deploy box'
    message = f"""Hello, you have been invited to create an account and join {user.username}'s organization {organization.name} please use
    the following link to sign up: http://localhost:8000/accounts/signup"""
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]

    send_mail(subject, message, from_email, recipient_list)