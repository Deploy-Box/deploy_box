from django.db import models
from django.conf import settings

from core.fields import ShortUUIDField


class Organization(models.Model):
    id = ShortUUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_projects(self) -> list:
        from projects.models import Project

        return list(Project.objects.filter(organization=self))

class OrganizationMember(models.Model):
    id = ShortUUIDField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=50,
        default="member",
        choices=[
            ("admin", "Admin"),
            ("member", "Member"),
        ],
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.organization.name}"


class PendingInvites(models.Model):
    id = ShortUUIDField(primary_key=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    email = models.EmailField()

    class Meta:
        unique_together = ['organization', 'email']

    def __str__(self):
        return self.email


class ProjectTransferInvitation(models.Model):
    """Model for tracking project ownership transfer invitations"""
    id = ShortUUIDField(primary_key=True)
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE)
    from_organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='sent_transfers')
    to_email = models.EmailField()
    to_name = models.CharField(max_length=255)
    to_company = models.CharField(max_length=255, blank=True, null=True)
    keep_developer = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        default="pending",
        choices=[
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
            ("expired", "Expired"),
        ],
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    to_organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='received_transfers', null=True, blank=True)

    def __str__(self):
        return f"Transfer {self.project.name} to {self.to_email}"

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class ProjectTransferAudit(models.Model):
    """Model for auditing project ownership transfers"""
    id = ShortUUIDField(primary_key=True)
    transfer_invitation = models.ForeignKey(ProjectTransferInvitation, on_delete=models.CASCADE)
    action = models.CharField(
        max_length=50,
        choices=[
            ("initiated", "Transfer Initiated"),
            ("accepted", "Transfer Accepted"),
            ("declined", "Transfer Declined"),
            ("expired", "Transfer Expired"),
            ("billing_transferred", "Billing Transferred"),
            ("infrastructure_transferred", "Infrastructure Transferred"),
        ],
    )
    details = models.TextField(blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} - {self.transfer_invitation.project.name}"


