from django.core.mail import send_mail
from core import settings
from django.contrib.sites.shortcuts import get_current_site

def send_invite_email(user, organization):
    subject = 'You have been invited to join an organization'
    message = f"Hello {user.username},\n\nYou have been invited to join the organization {organization.name}.\n\nBest regards,\nThe Team"
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]

    send_mail(subject, message, from_email, recipient_list)