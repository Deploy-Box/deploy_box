import base64
import json
import logging
import re

import qrcode
from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View
from io import BytesIO
from typing import cast

from accounts.models import UserProfile
from deploy_box_apis.views import get_project_api_info
from organizations.forms import (
    OrganizationMemberForm,
    NonexistantOrganizationMemberForm,
)
from organizations.models import (
    Organization,
    OrganizationMember,
    PendingInvites,
    ProjectTransferInvitation,
)
from projects.forms import ProjectCreateFormWithMembers, ProjectSettingsForm
from projects.models import Project, ProjectMember
from stacks.forms import EnvFileUploadForm, StackSettingsForm, EnvironmentVariablesForm
from stacks.models import PurchasableStack, Stack
from stacks.resources.resources_manager import ResourcesManager

logger = logging.getLogger(__name__)


class DashboardView(View):
    """Class-based view for all dashboard-related functionality."""

    
    def get(self, request: HttpRequest) -> HttpResponse:
        """Main dashboard view."""
        user = cast(UserProfile, request.user)
        logger.info(f"Dashboard accessed by user: {user.username}")
        organizations = Organization.objects.filter(organizationmember__user=user)
        projects = Project.objects.filter(projectmember__user=user)
        logger.info(
            f"Found {organizations.count()} organizations and {projects.count()} projects for user"
        )

        # If user has organizations, redirect to the first one
        first_organization = organizations.first()
        if first_organization:
            print(f"Redirecting to organization dashboard for organization: {first_organization.id}")
            return redirect('main_site:organization_dashboard', organization_id=first_organization.id)
        else:
            # Show welcome screen for users with no organizations
            print("Showing welcome screen for users with no organizations")
            return render(
                request,
                "dashboard/organization_select.html",
                {
                    "user": user,
                    "organizations": organizations,
                    "projects": projects,
                    "user_organizations": organizations,
                    "current_organization_id": None,
                    "current_project_id": None,
                    "current_stack_id": None,
                },
            )

    
    def organization_select(self, request: HttpRequest) -> HttpResponse:
        """Organization selection view - shows all organizations user has access to."""
        user = cast(UserProfile, request.user)
        logger.info(f"Organization select accessed by user: {user.username}")
        organizations = Organization.objects.filter(organizationmember__user=user)
        projects = Project.objects.filter(projectmember__user=user)
        logger.info(
            f"Found {organizations.count()} organizations for user"
        )

        return render(
            request,
            "dashboard/organization_select.html",
            {
                "user": user,
                "organizations": organizations,
                "projects": projects,
                "user_organizations": organizations,
                "current_organization_id": None,
                "current_project_id": None,
                "current_stack_id": None,
            },
        )

    
    def organization_dashboard(self, request: HttpRequest, organization_id: str) -> HttpResponse:
        """Organization-specific dashboard."""
        user = cast(UserProfile, request.user)
        organization = Organization.objects.get(id=organization_id)
        members = OrganizationMember.objects.filter(organization=organization)
        projects = Project.objects.filter(organization_id=organization_id)
        is_admin = OrganizationMember.objects.filter(
            organization=organization, user=user, role="admin"
        ).exists()

        # Get all organizations for the user for dropdown
        user_organizations = Organization.objects.filter(organizationmember__user=user)

        return render(
            request,
            "dashboard/organization_dashboard.html",
            {
                "user": user,
                "organization": organization,
                "members": members,
                "is_admin": is_admin,
                "projects": projects,
                "user_organizations": user_organizations,
                "current_organization_id": organization_id,
            },
        )

    
    def organization_billing(self, request: HttpRequest, organization_id: str) -> HttpResponse:
        """Organization billing page.
        
        Renders the page shell immediately. Payment methods, usage stats, and
        billing history are loaded asynchronously via JavaScript after page load.
        """
        user = cast(UserProfile, request.user)
        organization = Organization.objects.get(id=organization_id)

        # Get all organizations for the user for dropdown
        user_organizations = Organization.objects.filter(organizationmember__user=user)

        return render(
            request,
            "dashboard/organization_billing.html",
            {
                "user": user,
                "organization": organization,
                "user_organizations": user_organizations,
                "current_organization_id": organization_id,
                "stripe_publishable_key": settings.STRIPE.get("PUBLISHABLE_KEY", None),
            },
        )

    
    def project_dashboard(self, request: HttpRequest, organization_id: str, project_id: str) -> HttpResponse:
        """Project-specific dashboard."""
        user = cast(UserProfile, request.user)
        project = Project.objects.get(id=project_id)

        # Handle project deletion
        if request.method == 'POST' and request.POST.get('action') == 'delete':
            # Check if user has permission to delete the project
            project_member = ProjectMember.objects.filter(user=user, project=project, role='admin').first()
            if project_member:
                project.delete()
                return redirect('main_site:organization_dashboard', organization_id=organization_id)
            else:
                # User doesn't have permission to delete
                pass  # Could add error handling here

        stacks = Stack.objects.filter(project_id=project_id).exclude(status="Deleted")

        # Check if user is admin of the project
        is_admin = ProjectMember.objects.filter(user=user, project=project, role='admin').exists()

        # Get all organizations and projects for the user for dropdowns
        user_organizations = Organization.objects.filter(organizationmember__user=user)
        user_projects = Project.objects.filter(projectmember__user=user)

        return render(
            request,
            "dashboard/project_dashboard.html",
            {
                "organization_id": organization_id,
                "project": project,
                "stacks": stacks,
                "user_organizations": user_organizations,
                "user_projects": user_projects,
                "current_organization_id": organization_id,
                "current_project_id": project_id,
                "is_admin": is_admin,
            },
        )

    
    def stack_dashboard(self, request: HttpRequest, organization_id: str, project_id: str, stack_id: str) -> HttpResponse:
        """Stack-specific dashboard."""
        user = cast(UserProfile, request.user)
        try:
            stack = Stack.objects.get(id=stack_id)
        except Stack.DoesNotExist:
            # Redirect to project dashboard if stack doesn't exist
            return redirect('main_site:project_dashboard', organization_id=organization_id, project_id=project_id)
        
        # Handle stack deletion
        if request.method == 'POST' and request.POST.get('action') == 'delete':
            # Check if user has permission to delete the stack (project admin)
            try:
                project = Project.objects.get(id=project_id)
                project_member = ProjectMember.objects.filter(user=user, project=project, role='admin').first()
                if project_member:
                    stack.delete()
                    return redirect('main_site:project_dashboard', organization_id=organization_id, project_id=project_id)
                else:
                    # User doesn't have permission to delete
                    pass  # Could add error handling here
            except Project.DoesNotExist:
                # Redirect to organization dashboard if project doesn't exist
                return redirect('main_site:organization_dashboard', organization_id=organization_id)

        # Get repository information if webhook exists
        try:
            from github.models import Webhook
            webhook = Webhook.objects.get(stack=stack)
            repository_name = webhook.repository
        except Webhook.DoesNotExist:
            repository_name = None

        form = EnvFileUploadForm()

        # Get all organizations and projects for the user for dropdowns
        user_organizations = Organization.objects.filter(organizationmember__user=user)
        user_projects = Project.objects.filter(projectmember__user=user)
        user_stacks = Stack.objects.filter(project_id=project_id)
        # Get the current project for context
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            # Redirect to organization dashboard if project doesn't exist
            return redirect('main_site:organization_dashboard', organization_id=organization_id)

        # Determine template based on stack type
        stack_type = stack.purchased_stack.type.lower()
        if stack_type == "mobile":
            template_name = "dashboard/mobile_stack_dashboard.html"
            frontend_url = "#"
        elif stack_type == "custom":
            template_name = "dashboard/custom_stack_dashboard.html"
            frontend_url = "#"
        else:
            template_name = "dashboard/generic_stack_dashboard.html"
            frontend_url = "#"

        qr = qrcode.QRCode(
            version = 4,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border = 4,
        )
        qr.add_data(frontend_url)
        qr.make(fit=True)

        img = qr.make_image(back_color="white", fill_color=(18, 185, 129))

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        qr_code = f"data:image/png;base64,{img_str}"

        infrastructure_wrappers, infrastructure_nodes, infrastructure_connections = [], [], []

        if stack_type == "mobile":
            infrastructure_wrappers = json.dumps([
                {
                    "id": "backend_services",
                    "label": "Backend Services",
                    "x": 400,
                    "y": 140,
                    "width": 750,
                    "height": 280,
                    "color": "rgba(34, 197, 94, 0.1)",
                    "borderColor": "#22c55e",
                    "nodeIds": ["express", "postgres", "redis", "websocket"]
                }
            ])
            infrastructure_nodes = json.dumps([
                {
                    "id": "mobile_app",
                    "label": "React Native App",
                    "sublabel": "iOS & Android",
                    "x": 50,
                    "y": 200,
                    "width": 180,
                    "height": 100,
                    "color": "#3b82f6",
                    "icon": "📱"
                },
                {
                    "id": "expo",
                    "label": "Expo",
                    "sublabel": "Framework",
                    "x": 50,
                    "y": 350,
                    "width": 180,
                    "height": 80,
                    "color": "#6366f1",
                    "icon": "⚡"
                },
                {
                    "id": "express",
                    "label": "Express API",
                    "sublabel": "Backend",
                    "x": 420,
                    "y": 180,
                    "width": 150,
                    "height": 100,
                    "color": "#10b981",
                    "icon": "🚀"
                },
                {
                    "id": "postgres",
                    "label": "PostgreSQL",
                    "sublabel": "Database",
                    "x": 620,
                    "y": 180,
                    "width": 150,
                    "height": 100,
                    "color": "#3b82f6",
                    "icon": "🗄️"
                },
                {
                    "id": "redis",
                    "label": "Redis",
                    "sublabel": "Cache",
                    "x": 820,
                    "y": 180,
                    "width": 150,
                    "height": 100,
                    "color": "#ef4444",
                    "icon": "⚡"
                },
                {
                    "id": "websocket",
                    "label": "WebSocket",
                    "sublabel": "Real-time",
                    "x": 1020,
                    "y": 180,
                    "width": 150,
                    "height": 100,
                    "color": "#a855f7",
                    "icon": "🔌"
                },
                {
                    "id": "workos",
                    "label": "WorkOS",
                    "sublabel": "Authentication",
                    "x": 620,
                    "y": 350,
                    "width": 170,
                    "height": 100,
                    "color": "#f59e0b",
                    "icon": "🔐"
                }
            ])
            infrastructure_connections = json.dumps([
                {"from": "mobile_app", "to": "express", "label": "HTTP/REST"},
                {"from": "expo", "to": "mobile_app", "label": "Powers"},
                {"from": "express", "to": "postgres", "label": "Queries"},
                {"from": "express", "to": "redis", "label": "Cache"},
                {"from": "mobile_app", "to": "websocket", "label": "Real-time"},
                {"from": "mobile_app", "to": "workos", "label": "Auth"},
                {"from": "express", "to": "workos", "label": "Validate"}
            ])

        qr = qrcode.QRCode(
            version = 4,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border = 4,
        )
        qr.add_data(frontend_url)
        qr.make(fit=True)

        img = qr.make_image(back_color="white", fill_color=(18, 185, 129))

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        qr_code = f"data:image/png;base64,{img_str}"
        fqdn = settings.HOST.lstrip('https://').rstrip('/')
        print(f"FQDN: {fqdn}")

        # Build resource data for mobile/custom dashboards (shared query for both JSON and map)
        if stack_type in ("mobile", "custom"):
            serialized_resources = DashboardView._get_serialized_resources(stack)
            stack_resources_json = json.dumps(serialized_resources)
            resource_map = {}
            for r in serialized_resources:
                type_name = re.sub(r"_\d+$", "", r.get("name", ""))
                if type_name:
                    resource_map[type_name] = r
        else:
            stack_resources_json = "[]"
            resource_map = {}

        return render(
            request,
            template_name,
            {
                "organization_id": organization_id,
                "project_id": project_id,
                "stack": stack,
                "project": project,
                "form": form,
                "user_organizations": user_organizations,
                "user_projects": user_projects,
                "user_stacks": user_stacks,
                "current_organization_id": organization_id,
                "current_project_id": project_id,
                "current_stack_id": stack_id,
                "repository_name": repository_name,
                "frontend_url": frontend_url,
                "qr_code": qr_code,
                "infrastructure_wrappers": infrastructure_wrappers,
                "infrastructure_nodes": infrastructure_nodes,
                "infrastructure_connections": infrastructure_connections,
                "stack_resources_json": stack_resources_json,
                "resource_map": resource_map,
                "fqdn": fqdn
            },
        )

    @staticmethod
    def _get_serialized_resources(stack) -> list:
        """Serialize all resources for a stack, returning a list of dicts."""
        resources = ResourcesManager.get_from_stack(stack)
        serialized = ResourcesManager.serialize(resources)
        return [r for r in serialized if r is not None]

    @staticmethod
    def _get_stack_resources_json(stack) -> str:
        """Serialize all resources for a stack to JSON for the frontend."""
        return json.dumps(DashboardView._get_serialized_resources(stack))

    @staticmethod
    def _get_stack_resources_map(stack) -> dict:
        """Build a dict of resources keyed by type name for template access."""
        resource_map = {}
        for r in DashboardView._get_serialized_resources(stack):
            type_name = re.sub(r"_\d+$", "", r.get("name", ""))
            if type_name:
                resource_map[type_name] = r
        return resource_map

    
    def add_org_members(self, request: HttpRequest, organization_id: str) -> HttpResponse:
        """Add organization members view."""
        user = cast(UserProfile, request.user)
        organization = Organization.objects.get(id=organization_id)
        form = OrganizationMemberForm()
        return render(
            request,
            "accounts/invite_org_member.html",
            {"organization": organization, "user": user, "form": form},
        )

    def add_nonexistant_org_members(self, request: HttpRequest, organization_id: str) -> HttpResponse:
        """Add non-existent organization members view."""
        user = cast(UserProfile, request.user)
        organization = Organization.objects.get(id=organization_id)
        form = NonexistantOrganizationMemberForm()
        return render(
            request,
            "accounts/invite_nonexistant_org_member.html",
            {"organization": organization, "user": user, "form": form},
        )

    
    def create_project_form(self, request: HttpRequest, organization_id: str) -> HttpResponse:
        """Create project form view."""
        form = ProjectCreateFormWithMembers()
        return render(
            request,
            "accounts/create_project_form.html",
            {"form": form, "organization_id": organization_id},
        )

    
    def organization_members(self, request: HttpRequest, organization_id: str) -> HttpResponse:
        """Organization members page."""
        user = cast(UserProfile, request.user)
        organization = Organization.objects.get(id=organization_id)
        members = OrganizationMember.objects.filter(organization=organization)
        pending_invites = PendingInvites.objects.filter(organization=organization)
        user_organizations = Organization.objects.filter(organizationmember__user=user)

        # Check if user is admin of this organization
        is_admin = OrganizationMember.objects.filter(
            organization=organization,
            user=user,
            role="admin"
        ).exists()

        return render(
            request,
            "dashboard/organization_members.html",
            {
                "user": user,
                "organization": organization,
                "members": members,
                "pending_invites": pending_invites,
                "user_organizations": user_organizations,
                "current_organization_id": organization_id,
                "is_admin": is_admin,
            },
        )

    
    def organization_settings(self, request: HttpRequest, organization_id: str) -> HttpResponse:
        """Organization settings page."""
        user = cast(UserProfile, request.user)
        organization = Organization.objects.get(id=organization_id)
        user_organizations = Organization.objects.filter(organizationmember__user=user)
        return render(
            request,
            "dashboard/organization_settings.html",
            {
                "user": user,
                "organization": organization,
                "user_organizations": user_organizations,
                "current_organization_id": organization_id,
            },
        )

    
    def project_settings(self, request: HttpRequest, organization_id: str, project_id: str) -> HttpResponse:
        """Project settings page."""
        user = cast(UserProfile, request.user)
        project = Project.objects.get(id=project_id)

        if request.method == 'POST':
            form = ProjectSettingsForm(request.POST, instance=project)
            if form.is_valid():
                form.save()
                messages.success(request, 'Project settings updated successfully')
                return redirect('main_site:project_settings', organization_id=organization_id, project_id=project_id)
        else:
            form = ProjectSettingsForm(instance=project)

        # Get all organizations and projects for the user for dropdowns
        user_organizations = Organization.objects.filter(organizationmember__user=user)
        user_projects = Project.objects.filter(projectmember__user=user)

        # Check if user is admin of the project
        is_admin = ProjectMember.objects.filter(user=user, project=project, role='admin').exists()

        return render(
            request,
            "dashboard/project_settings.html",
            {
                "user": user,
                "project": project,
                "form": form,
                "user_organizations": user_organizations,
                "user_projects": user_projects,
                "current_organization_id": organization_id,
                "current_project_id": project_id,
                "is_admin": is_admin,
            },
        )

    
    def stack_settings(self, request: HttpRequest, organization_id: str, project_id: str, stack_id: str) -> HttpResponse:
        """Stack settings page."""
        user = cast(UserProfile, request.user)
        stack = Stack.objects.get(id=stack_id)

        if request.method == 'POST':
            form = StackSettingsForm(request.POST, instance=stack)
            if form.is_valid():
                form.save()
                messages.success(request, 'Stack settings updated successfully')
                return redirect('main_site:stack_settings', organization_id=organization_id, project_id=project_id, stack_id=stack_id)
        else:
            form = StackSettingsForm(instance=stack)

        # Get all organizations and projects for the user for dropdowns
        user_organizations = Organization.objects.filter(organizationmember__user=user)
        user_projects = Project.objects.filter(projectmember__user=user)
        user_stacks = Stack.objects.filter(project_id=project_id)
        # Get the current project for context
        project = Project.objects.get(id=project_id)

        return render(
            request,
            "dashboard/stack_settings.html",
            {
                "organization_id": organization_id,
                "project_id": project_id,
                "stack": stack,
                "project": project,
                "form": form,
                "user_organizations": user_organizations,
                "user_projects": user_projects,
                "user_stacks": user_stacks,
                "current_organization_id": organization_id,
                "current_project_id": project_id,
                "current_stack_id": stack_id,
            },
        )

    
    def environment_variables(self, request: HttpRequest, organization_id: str, project_id: str, stack_id: str) -> HttpResponse:
        """Environment variables configuration page."""
        user = cast(UserProfile, request.user)
        stack = Stack.objects.get(id=stack_id)

        if request.method == 'POST':
            form = EnvironmentVariablesForm(request.POST, request.FILES)
            if form.is_valid():
                env_variables = form.cleaned_data.get('env_variables', '')

                # Save the environment variables
                if env_variables.strip():
                    # Parse the environment variables string into a dictionary
                    env_dict = {}
                    for line in env_variables.strip().split('\n'):
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                env_dict[key.strip()] = value.strip()

                    # Call the post_stack_env function with the dictionary
                    try:
                        result = post_stack_env(
                            stack_id=stack_id,
                            selected_frameworks=stack.purchased_stack.type.lower(),
                            selected_locations="none",  # You might want to make this configurable
                            env_dict=env_dict
                        )

                        if result.status_code == 200:
                            messages.success(request, 'Environment variables updated successfully')
                        else:
                            messages.error(request, 'Failed to update environment variables')
                    except Exception as e:
                        messages.error(request, f'Error updating environment variables: {str(e)}')
                else:
                    messages.warning(request, 'No environment variables provided.')

                return redirect('main_site:environment_variables', organization_id=organization_id, project_id=project_id, stack_id=stack_id)
        else:
            # Initialize form with existing environment variables if any
            initial_data = {}
            # You could load existing env vars here: initial_data['env_variables'] = stack.get_env_variables()
            form = EnvironmentVariablesForm(initial=initial_data)

        # Get all organizations and projects for the user for dropdowns
        user_organizations = Organization.objects.filter(organizationmember__user=user)
        user_projects = Project.objects.filter(projectmember__user=user)
        user_stacks = Stack.objects.filter(project_id=project_id)
        # Get the current project for context
        project = Project.objects.get(id=project_id)

        return render(
            request,
            "dashboard/environment_variables.html",
            {
                "organization_id": organization_id,
                "project_id": project_id,
                "stack": stack,
                "project": project,
                "form": form,
                "user_organizations": user_organizations,
                "user_projects": user_projects,
                "user_stacks": user_stacks,
                "current_organization_id": organization_id,
                "current_project_id": project_id,
                "current_stack_id": stack_id,
            },
        )

    
    def environments(self, request: HttpRequest, organization_id: str, project_id: str, stack_id: str) -> HttpResponse:
        """Environment management page."""
        user = cast(UserProfile, request.user)
        project = Project.objects.get(id=project_id)
        stack = Stack.objects.get(id=stack_id)

        # Get all organizations and projects for the user for dropdowns
        user_organizations = Organization.objects.filter(organizationmember__user=user)
        user_projects = Project.objects.filter(projectmember__user=user)

        # Check if user is admin of the project
        is_admin = ProjectMember.objects.filter(user=user, project=project, role='admin').exists()

        return render(
            request,
            "dashboard/environments.html",
            {
                "organization_id": organization_id,
                "project_id": project_id,
                "stack_id": stack_id,
                "project": project,
                "stack": stack,
                "user_organizations": user_organizations,
                "user_projects": user_projects,
                "current_organization_id": organization_id,
                "current_project_id": project_id,
                "current_stack_id": stack_id,
                "is_admin": is_admin,
            },
        )

    
    def project_transfer_accept(self, request: HttpRequest, transfer_id: str) -> HttpResponse:
        """Project transfer acceptance page."""
        user = cast(UserProfile, request.user)
        
        # Get user's organizations for navbar context
        user_organizations = Organization.objects.filter(organizationmember__user=user)
        first_user_organization = user_organizations.first()

        if first_user_organization is None:
            current_organization_id = ""
        else:
            current_organization_id = first_user_organization.id

        # Get user's projects for navbar context
        user_projects = Project.objects.filter(projectmember__user=user)
        
        # Get user's stacks for navbar context
        user_stacks = Stack.objects.filter(project__projectmember__user=user)
        
        try:
            transfer_invitation = ProjectTransferInvitation.objects.get(id=transfer_id)
            
            # Check if the transfer is for this user
            if transfer_invitation.to_email != user.email:
                return render(
                    request,
                    "dashboard/project_transfer_accept.html",
                    {
                        "transfer_invitation": None,
                        "user_organizations": user_organizations,
                        "user_projects": user_projects,
                        "user_stacks": user_stacks,
                        "current_organization_id": current_organization_id,
                        "current_project_id": "",
                        "current_stack_id": "",
                    }
                )
            
            return render(
                request,
                "dashboard/project_transfer_accept.html",
                {
                    "transfer_invitation": transfer_invitation,
                    "user_organizations": user_organizations,
                    "user_projects": user_projects,
                    "user_stacks": user_stacks,
                    "current_organization_id": current_organization_id,
                    "current_project_id": "",
                    "current_stack_id": "",
                }
            )
            
        except ProjectTransferInvitation.DoesNotExist:
            return render(
                request,
                "dashboard/project_transfer_accept.html",
                {
                    "transfer_invitation": None,
                    "user_organizations": user_organizations,
                    "user_projects": user_projects,
                    "user_stacks": user_stacks,
                    "current_organization_id": current_organization_id,
                    "current_project_id": "",
                    "current_stack_id": "",
                }
            )

    
    def transfer_invitations(self, request: HttpRequest) -> HttpResponse:
        """View for transfer invitations."""
        user = cast(UserProfile, request.user)
        invitations = ProjectTransferInvitation.objects.filter(
            to_email=user.email, status="pending"
        )
        
        # Get user's organizations for navbar context
        user_organizations = Organization.objects.filter(organizationmember__user=user)
        first_user_organization = user_organizations.first()

        if first_user_organization is None:
            current_organization_id = ""
        else:
            current_organization_id = first_user_organization.id

        # Get user's projects for navbar context
        user_projects = Project.objects.filter(projectmember__user=user)
        
        # Get user's stacks for navbar context
        user_stacks = Stack.objects.filter(project__projectmember__user=user)
        
        return render(
            request,
            "dashboard/transfer_invitations.html",
            {
                "invitations": invitations,
                "user": user,
                "user_organizations": user_organizations,
                "user_projects": user_projects,
                "user_stacks": user_stacks,
                "current_organization_id": current_organization_id,
                "current_project_id": "",
                "current_stack_id": "",
            },
        )

    
    def stack_marketplace(self, request: HttpRequest, organization_id: str, project_id: str) -> HttpResponse:
        """View for the stack marketplace where users can purchase stacks."""
        user = cast(UserProfile, request.user)
        
        # Verify user has access to this organization and project
        try:
            organization = Organization.objects.get(id=organization_id)
            project = Project.objects.get(id=project_id, organization=organization)
            
            # Check if user is a member of the organization
            if not OrganizationMember.objects.filter(user=user, organization=organization).exists():
                messages.error(request, "You don't have access to this organization.")
                return redirect('main_site:dashboard')
                
        except (Organization.DoesNotExist, Project.DoesNotExist):
            messages.error(request, "Organization or project not found.")
            return redirect('main_site:dashboard')
                
        # Fetch all purchasable stacks and their pricing
        purchasable_stacks = []
        try:
            db_stacks = PurchasableStack.objects.all()
            
            for stack in db_stacks:
                # Map stack type to icon and color
                icon_map = {
                    'MERN': '⚛️',
                    'DJANGO': '🐍',
                    'MEAN': '🅰️',
                    'LAMP': '🐘',
                    'STATIC': '🌐',
                    'SOCIAL': '💬',
                }
                
                color_map = {
                    'BASIC': 'emerald',
                    'PREMIUM': 'amber',
                    'PRO': 'purple'
                }
                
                purchasable_stacks.append({
                    'id': str(stack.id),
                    'name': stack.name,
                    'type': stack.type,
                    'variant': stack.variant,
                    'description': stack.description,
                    'features': stack.features,
                    'icon': icon_map.get(stack.type, '📦'),
                    'color': color_map.get(stack.variant, 'emerald'),
                    'popular': False,  # Could be determined by sales volume or admin setting
                    'is_from_database': True  # Flag to identify database entries
                })
                
        except Exception as e:
            logger.error(f"Error fetching purchasable stacks: {e}")

        # Get all organizations and projects for the user for dropdowns
        user_organizations = Organization.objects.filter(organizationmember__user=user)
        user_projects = Project.objects.filter(projectmember__user=user)
        user_stacks = Stack.objects.filter(project__projectmember__user=user)
        
        return render(
            request,
            "dashboard/stack_marketplace.html",
            {
                "organization": organization,
                "project": project,
                "purchasable_stacks": purchasable_stacks,
                "user": user,
                "user_organizations": user_organizations,
                "user_projects": user_projects,
                "user_stacks": user_stacks,
                "current_organization_id": organization_id,
                "current_project_id": project_id,
                "current_stack_id": "",
            },
        )

    
    def api_marketplace(self, request: HttpRequest, organization_id: str, project_id: str) -> HttpResponse:
        """View for the API marketplace where users can purchase APIs."""
        user = cast(UserProfile, request.user)
        
        # Verify user has access to this organization and project
        try:
            organization = Organization.objects.get(id=organization_id)
            project = Project.objects.get(id=project_id, organization=organization)
            
            # Check if user is a member of the organization
            if not OrganizationMember.objects.filter(user=user, organization=organization).exists():
                messages.error(request, "You don't have access to this organization.")
                return redirect('main_site:dashboard')
                
        except (Organization.DoesNotExist, Project.DoesNotExist):
            messages.error(request, "Organization or project not found.")
            return redirect('main_site:dashboard')

        # Get all organizations and projects for the user for dropdowns
        user_organizations = Organization.objects.filter(organizationmember__user=user)
        user_projects = Project.objects.filter(projectmember__user=user)
        user_stacks = Stack.objects.filter(project__projectmember__user=user)

        deploy_box_api_render_info = get_project_api_info(project_id=project_id)

        render_data = {
            "organization": organization,
            "project": project,
            "user": user,
            "user_organizations": user_organizations,
            "user_projects": user_projects,
            "user_stacks": user_stacks,
            "current_organization_id": organization_id,
            "current_project_id": project_id,
            "current_stack_id": "",
        }

        render_data.update(deploy_box_api_render_info)
        return render(
            request,
            "dashboard/api_marketplace.html",
            render_data,
        )

    
    def stack_details(self, request: HttpRequest, organization_id: str, project_id: str, stack_id: str) -> HttpResponse:
        """View for individual stack details page."""
        user = cast(UserProfile, request.user)
        
        # Verify user has access to this organization and project
        try:
            organization = Organization.objects.get(id=organization_id)
            project = Project.objects.get(id=project_id, organization=organization)
            
            # Check if user is a member of the organization
            if not OrganizationMember.objects.filter(user=user, organization=organization).exists():
                messages.error(request, "You don't have access to this organization.")
                return redirect('main_site:dashboard')
                
        except (Organization.DoesNotExist, Project.DoesNotExist):
            messages.error(request, "Organization or project not found.")
            return redirect('main_site:dashboard')

        # Find the specific stack from the hardcoded list
        available_stacks = [
            # ... (same list as in stack_marketplace)
        ]
        
        # Find the stack by ID
        stack = None
        for s in available_stacks:
            if s['id'] == stack_id:
                stack = s
                break
        
        if not stack:
            messages.error(request, "Stack not found.")
            return redirect('main_site:stack_marketplace', organization_id=organization_id, project_id=project_id)

        # Get all organizations and projects for the user for dropdowns
        user_organizations = Organization.objects.filter(organizationmember__user=user)
        user_projects = Project.objects.filter(projectmember__user=user)
        user_stacks = Stack.objects.filter(project__projectmember__user=user)

        return render(
            request,
            "dashboard/stack_details.html",
            {
                "organization": organization,
                "project": project,
                "stack": stack,
                "user": user,
                "user_organizations": user_organizations,
                "user_projects": user_projects,
                "user_stacks": user_stacks,
                "current_organization_id": organization_id,
                "current_project_id": project_id,
                "current_stack_id": stack_id,
            },
        )


dashboard_view = DashboardView()
