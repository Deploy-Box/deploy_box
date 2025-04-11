from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from accounts.models import Organization, OrganizationMember, Project, ProjectMember

@receiver(post_save, sender=User)
def create_user_organization_and_project(sender, instance, created, **kwargs):
    if created:
        # Create a personal organization for the user
        organization = Organization.objects.create(
            name=f"{instance.username}'s Organization"
        )
        
        # Add the user as an admin of their organization
        OrganizationMember.objects.create(
            user=instance,
            organization=organization,
            role="admin"
        )
        
        # Create a default project in the organization
        project = Project.objects.create(
            name="My First Project",
            description="Welcome to your first project!",
            organization=organization
        )
        
        # Add the user as an admin of the project
        ProjectMember.objects.create(
            user=instance,
            project=project,
            role="admin"
        ) 