from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.conf import settings
from django.contrib import messages
from django.views import View
from typing import cast
import logging
import calendar
import stripe
import qrcode
from io import BytesIO
import base64


from stacks.stack_managers.get_manager import get_stack_manager
from accounts.forms import CustomUserCreationForm
from accounts.models import UserProfile
from organizations.models import Organization, OrganizationMember, PendingInvites, ProjectTransferInvitation
from organizations.forms import (
    OrganizationMemberForm,
    NonexistantOrganizationMemberForm,
)
from organizations.services import get_organizations
from projects.forms import ProjectCreateFormWithMembers, ProjectSettingsForm
from projects.models import Project, ProjectMember
from stacks.forms import EnvFileUploadForm, StackSettingsForm, EnvironmentVariablesForm
from stacks.models import PurchasableStack, Stack
from core.decorators import oauth_required

logger = logging.getLogger(__name__)


# Basic Routes
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "home.html", {"show_footer": False})


def stacks(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks.html", {"show_footer": False})


def mern_stack(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks/mern_stack.html", {"show_footer": False})


def django_stack(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks/django_stack.html", {"show_footer": False})


def mean_stack(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks/mean_stack.html", {"show_footer": False})


def lamp_stack(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks/lamp_stack.html", {"show_footer": False})


def mevn_stack(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks/mevn_stack.html", {"show_footer": False})


def pricing(request: HttpRequest) -> HttpResponse:
    return render(request, "pricing.html", {"show_footer": False})


def profile(request: HttpRequest) -> HttpResponse:
    return render(request, "profile.html", {})


def maintenance(request: HttpRequest) -> HttpResponse:
    return render(request, "maintenance.html", {})


class DashboardView(View):
    """Class-based view for all dashboard-related functionality."""


    @oauth_required()
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
                "dashboard/welcome.html",
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

    @oauth_required()
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

    @oauth_required()
    def organization_billing(self, request: HttpRequest, organization_id: str) -> HttpResponse:
        """Organization billing page."""
        user = cast(UserProfile, request.user)
        organization = Organization.objects.get(id=organization_id)

        # Get all organizations for the user for dropdown
        user_organizations = Organization.objects.filter(organizationmember__user=user)

        # Get payment methods for the organization
        payment_methods = []
        try:
            stripe.api_key = settings.STRIPE.get("SECRET_KEY")

            if organization.stripe_customer_id:
                # Get all payment methods for the customer
                stripe_payment_methods = stripe.PaymentMethod.list(
                    customer=organization.stripe_customer_id,
                    type="card"
                )

                # Get the customer to find the default payment method
                customer = stripe.Customer.retrieve(organization.stripe_customer_id)
                default_payment_method_id = customer.invoice_settings.default_payment_method if customer.invoice_settings else None

                # Format payment methods
                for pm in stripe_payment_methods.data:
                    if pm.card:
                        payment_methods.append({
                            "id": pm.id,
                            "brand": pm.card.brand,
                            "last4": pm.card.last4,
                            "exp_month": pm.card.exp_month,
                            "exp_year": pm.card.exp_year,
                            "is_default": pm.id == default_payment_method_id,
                        })
        except Exception as e:
            # Log the error but don't fail the page
            logger.error(f"Error fetching payment methods: {e}")

        # --- PLACEHOLDERS BEGIN ---

        # Placeholder values for missing variables (set real logic when available)
        try:
            daily_usage = float(getattr(organization, 'daily_usage', 1.23))
        except Exception:
            daily_usage = 1.23

        try:
            current_usage = float(getattr(organization, 'current_usage', 42.42))
        except Exception:
            current_usage = 42.42

        try:
            projected_monthly_usage = float(getattr(organization, 'projected_monthly_usage', 123.45))
        except Exception:
            projected_monthly_usage = 123.45

        import datetime
        try:
            # Try to use a real month start attribute; default to first of this month
            month_start = getattr(organization, 'month_start', datetime.datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0))
        except Exception:
            month_start = datetime.datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        try:
            billing_history_records = getattr(organization, 'billing_history_records', [
                # Example placeholder record(s).
                {"date": "2024-06-01", "amount": "29.99", "status": "Paid"},
                {"date": "2024-05-01", "amount": "19.99", "status": "Paid"},
            ])
        except Exception:
            billing_history_records = [
                {"date": "2024-06-01", "amount": "29.99", "status": "Paid"},
                {"date": "2024-05-01", "amount": "19.99", "status": "Paid"},
            ]
        # --- PLACEHOLDERS END ---

        return render(
            request,
            "dashboard/organization_billing.html",
            {
                "user": user,
                "organization": organization,
                "user_organizations": user_organizations,
                "current_organization_id": organization_id,
                "payment_methods": payment_methods,
                "stripe_publishable_key": settings.STRIPE.get("PUBLISHABLE_KEY", None),
                "current_daily_usage": f"{daily_usage:.2f}",
                "current_usage": f"{current_usage:.2f}",
                "projected_monthly_usage": f"{projected_monthly_usage:.2f}",
                "month_start_formatted": month_start.strftime("%b 1, %Y"),
                "billing_history_records": billing_history_records,
            },
        )

    @oauth_required()
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

        stacks = Stack.objects.filter(project_id=project_id).exclude(status="DELETED")

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

    @oauth_required()
    def stack_dashboard(self, request: HttpRequest, organization_id: str, project_id: str, stack_id: str) -> HttpResponse:
        """Stack-specific dashboard."""
        user = cast(UserProfile, request.user)
        try:
            stack = Stack.objects.get(id=stack_id)
        except Stack.DoesNotExist:
            # Redirect to project dashboard if stack doesn't exist
            return redirect('main_site:project_dashboard', organization_id=organization_id, project_id=project_id)
        
        stack_manager = get_stack_manager(stack)

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
        if stack_type == "mern":
            template_name = "dashboard/mern_stack_dashboard.html"
            frontend_url = stack.mern_frontend_url
        elif stack_type == "django":
            template_name = "dashboard/django_stack_dashboard.html"
            frontend_url = stack.django_url
        elif stack_type == "redis":
            template_name = "dashboard/redis_stack_dashboard.html"
            frontend_url = stack.redis_url
        elif stack_type == "pong":
            template_name = "dashboard/pong_stack_dashboard.html"
            frontend_url = stack.redis_url
        else:
            template_name = "dashboard/stack_dashboard.html"
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

        # Prepare infrastructure data for Pong stack
        infrastructure_wrappers, infrastructure_nodes, infrastructure_connections = stack_manager.get_infrastructure_diagram_data()
            
        if stack_type == "pong":
            import json
            pong_infrastructure_wrappers = json.dumps([
                {
                    "id": "vm",
                    "label": "Virtual Machine",
                    "x": 280,
                    "y": 150,
                    "width": 500,
                    "height": 200,
                    "color": "rgba(139, 92, 246, 0.1)",
                    "borderColor": "#8b5cf6",
                    "nodeIds": ["frontend", "backend"]
                }
            ])
            pong_infrastructure_nodes = json.dumps([
                {
                    "id": "public_ip",
                    "label": "Public IP",
                    "sublabel": "Network",
                    "x": 50,
                    "y": 225,
                    "width": 150,
                    "height": 80,
                    "color": "#f59e0b",
                    "icon": "🌍"
                },
                {
                    "id": "proxy",
                    "label": "Deploy Box Proxy",
                    "sublabel": "Load Balancer",
                    "x": 260,
                    "y": 210,
                    "width": 140,
                    "height": 110,
                    "color": "#ec4899",
                    "icon": "🔀"
                },
                {
                    "id": "frontend",
                    "label": "Pong Web App",
                    "sublabel": "Frontend",
                    "x": 330,
                    "y": 200,
                    "width": 150,
                    "height": 100,
                    "color": "#10b981",
                    "icon": "🌐"
                },
                {
                    "id": "backend",
                    "label": "PostgreSQL",
                    "sublabel": "Database",
                    "x": 580,
                    "y": 200,
                    "width": 150,
                    "height": 100,
                    "color": "#3b82f6",
                    "icon": "🗄️"
                },
                {
                    "id": "disk",
                    "label": "Persistent Disk",
                    "sublabel": "Storage",
                    "x": 600,
                    "y": 500,
                    "width": 180,
                    "height": 100,
                    "color": "#64748b",
                    "icon": "💾"
                }
            ])
            pong_infrastructure_connections = json.dumps([
                {"from": "public_ip", "to": "proxy", "label": "Internet"},
                {"from": "proxy", "to": "vm", "label": "Forwarded"},
                {"from": "frontend", "to": "backend", "label": "Data Connection"},
                {"from": "vm", "to": "disk", "label": "Mounted"}
            ])

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
            },
        )

    @oauth_required()
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



    @oauth_required()
    def create_project_form(self, request: HttpRequest, organization_id: str) -> HttpResponse:
        """Create project form view."""
        form = ProjectCreateFormWithMembers()
        return render(
            request,
            "accounts/create_project_form.html",
            {"form": form, "organization_id": organization_id},
        )

    @oauth_required()
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

    @oauth_required()
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

    @oauth_required()
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

    @oauth_required()
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

    @oauth_required()
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

    @oauth_required()
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

    @oauth_required()
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

    @oauth_required()
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

    @oauth_required()
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
                    'LAMP': '🐘'
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

    @oauth_required()
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


        from deploy_box_apis.views import get_project_api_info

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

    @oauth_required()
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


class PaymentView(View):
    """Class-based view for all payment-related functionality."""

    STRIPE_PUBLISHABLE_KEY = settings.STRIPE.get("PUBLISHABLE_KEY", None)

    @oauth_required()
    def home_page_view(self, request: HttpRequest, variant: str) -> HttpResponse:
        """Payment home page view - redirects to new stacks marketplace."""
        # Redirect to the new stacks marketplace with the variant as a query parameter
        return redirect(f'/stacks-marketplace/?variant={variant}')

    def _generate_stack_features(self, stack_type: str, variant: str) -> list:
        """Generate features list based on stack type and variant."""
        base_features = {
            'MERN': [
                'MongoDB Database',
                'Express.js Backend API',
                'React Frontend',
                'Node.js Runtime',
                'Docker Containerization',
                'Auto-deployment'
            ],
            'DJANGO': [
                'Django Backend',
                'PostgreSQL Database',
                'React Frontend',
                'Docker Containerization',
                'Admin Interface',
                'Auto-deployment'
            ],
            'MEAN': [
                'MongoDB Database',
                'Express.js Backend API',
                'Angular Frontend',
                'Node.js Runtime',
                'Docker Containerization',
                'Auto-deployment'
            ],
            'LAMP': [
                'Apache Web Server',
                'MySQL Database',
                'PHP Backend',
                'Docker Containerization',
                'Basic Security',
                'Auto-deployment'
            ]
        }
        
        premium_features = {
            'MERN': [
                'Everything in Basic',
                'Redis Caching',
                'Advanced Security',
                'Performance Monitoring',
                'CI/CD Pipeline',
                'Priority Support'
            ],
            'DJANGO': [
                'Everything in Basic',
                'Redis Caching',
                'Celery Task Queue',
                'Advanced Security',
                'Performance Monitoring',
                'Priority Support'
            ],
            'MEAN': [
                'Everything in Basic',
                'Redis Caching',
                'Advanced Security',
                'Performance Monitoring',
                'CI/CD Pipeline',
                'Priority Support'
            ],
            'LAMP': [
                'Everything in Basic',
                'Redis Caching',
                'Advanced Security',
                'Performance Monitoring',
                'SSL Certificate',
                'Priority Support'
            ]
        }
        
        pro_features = {
            'MERN': [
                'Everything in Premium',
                'Microservices Architecture',
                'Advanced Caching (Redis + Memcached)',
                'Load Balancing',
                'Auto-scaling Infrastructure',
                '24/7 Priority Support',
                'Custom Domain Setup',
                'Advanced Analytics'
            ],
            'DJANGO': [
                'Everything in Premium',
                'Microservices Architecture',
                'Advanced Caching (Redis + Memcached)',
                'Load Balancing',
                'Auto-scaling Infrastructure',
                '24/7 Priority Support',
                'Custom Domain Setup',
                'Advanced Analytics'
            ],
            'MEAN': [
                'Everything in Premium',
                'Microservices Architecture',
                'Advanced Caching (Redis + Memcached)',
                'Load Balancing',
                'Auto-scaling Infrastructure',
                '24/7 Priority Support',
                'Custom Domain Setup',
                'Advanced Analytics'
            ],
            'LAMP': [
                'Everything in Premium',
                'Microservices Architecture',
                'Advanced Caching (Redis + Memcached)',
                'Load Balancing',
                'Auto-scaling Infrastructure',
                '24/7 Priority Support',
                'Custom Domain Setup',
                'Advanced Analytics'
            ]
        }
        
        if variant.upper() == 'BASIC' or variant.upper() == 'FREE':
            return base_features.get(stack_type, ['Basic features'])
        elif variant.upper() == 'PREMIUM':
            return premium_features.get(stack_type, ['Premium features'])
        elif variant.upper() == 'PRO':
            return pro_features.get(stack_type, ['Pro features'])
        else:
            return base_features.get(stack_type, ['Basic features'])

    def stacks_marketplace_view(self, request: HttpRequest) -> HttpResponse:
        """Stacks marketplace view with filter options."""
        is_authenticated = request.user.is_authenticated

        if is_authenticated:
            user_profile = cast(UserProfile, request.user)
            organizations = get_organizations(user_profile)

            # Look through orgs until we find one with projects
            organization = None
            projects = []
            project = None
            for org in organizations:
                org_projects = org.get_projects()
                print(org_projects)
                if org_projects:
                    organization = org
                    projects = org_projects
                    project = projects[0]
                    break

        else:
            organization = None
            project = None

        print(organization)
        print(project)
        
        # Get variant from query parameter, default to 'BASIC'
        variant = request.GET.get('variant', 'BASIC').upper()
        
        # Get stacks with pricing information (same as stack marketplace)
        import stripe
        stripe.api_key = settings.STRIPE.get("SECRET_KEY")
        
        stack_options = []
        db_stacks = PurchasableStack.objects.all()  # Get all stacks, filter in template
        print("here is stacks: ", db_stacks)
        
        for stack in db_stacks:
            try:
                # Map stack type to icon and color
                icon_map = {
                    'MERN': '⚛️',
                    'DJANGO': '🐍',
                    'MEAN': '🅰️',
                    'LAMP': '🐘'
                }
                
                color_map = {
                    'BASIC': 'emerald',
                    'PREMIUM': 'amber',
                    'PRO': 'purple',
                    'FREE': 'emerald'
                }
   
                stack_options.append({
                    'id': str(stack.id),
                    'name': stack.name,
                    'type': stack.type,
                    'variant': stack.variant,
                    'description': stack.description,
                    'features': stack.features,
                    'icon': icon_map.get(stack.type, '📦'),
                    'color': color_map.get(stack.variant, 'emerald'),
                    'popular': False,
                    'is_from_database': True
                })
            except stripe.error.StripeError as e: # type: ignore[attr-defined]
                # Log error but continue with other stacks
                logger.error(f"Error fetching price for stack {stack.id}: {e}")
                continue
        
        return render(
            request,
            "payments/stacks_marketplace.html",
            {
                "organization_id": organization.id if organization else None,
                "project_id": project.id if project else None,
                "stack_options": stack_options,
                "selected_variant": variant,
            },
        )

    @oauth_required()
    def add_card_view(self, request: HttpRequest) -> HttpResponse:
        """Add card view."""
        return render(
            request,
            "payments/add-card.html",
            {"stripe_publishable_key": self.STRIPE_PUBLISHABLE_KEY},
        )

    @oauth_required()
    def success_view(self, request: HttpRequest) -> HttpResponse:
        """Payment success view."""
        return render(request, "payments/success.html")

    @oauth_required()
    def cancelled_view(self, request: HttpRequest) -> HttpResponse:
        """Payment cancelled view."""
        return render(request, "payments/cancelled.html")


class AuthView(View):
    """Class-based view for all authentication-related functionality."""

    def login(self, request: HttpRequest) -> HttpResponse:
        """Login view."""
        return render(request, "accounts/login.html", {})

    def password_reset(self, request: HttpRequest) -> HttpResponse:
        """Password reset view."""
        return render(request, "accounts/password_reset.html", {})

    def password_reset_confirm(self, request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
        """Password reset confirm view."""
        return render(
            request,
            "accounts/password_reset_confirm.html",
            {"uidb64": uidb64, "token": token},
        )

    def signup(self, request: HttpRequest) -> HttpResponse:
        """Signup view."""
        # Handle both 'invite' and 'invite_id' parameters for backward compatibility
        invite_id = request.GET.get('invite_id') or request.GET.get('invite')
        transfer_id = request.GET.get('transfer_id')
        invite_data = None
        transfer_data = None

        if invite_id:
            try:
                pending_invite = PendingInvites.objects.get(id=invite_id)
                invite_data = {
                    'invite_id': invite_id,
                    'organization_name': pending_invite.organization.name,
                    'organization_email': pending_invite.organization.email,
                    'invite_email': pending_invite.email
                }
                
                # If there's also a transfer_id, get transfer data
                if transfer_id:
                    try:
                        transfer_invitation = ProjectTransferInvitation.objects.get(id=transfer_id, status="pending")
                        transfer_data = {
                            'transfer_id': transfer_id,
                            'project_name': transfer_invitation.project.name,
                            'developer_name': transfer_invitation.from_organization.name,
                            'keep_developer': transfer_invitation.keep_developer,
                            'expires_at': transfer_invitation.expires_at.strftime('%B %d, %Y')
                        }
                    except ProjectTransferInvitation.DoesNotExist:
                        # Invalid transfer ID - will be handled in template
                        pass
                        
            except PendingInvites.DoesNotExist:
                # Invalid invite ID - will be handled in template
                pass

        return render(request, "accounts/signup.html", {
            "form": CustomUserCreationForm,
            "invite_data": invite_data,
            "transfer_data": transfer_data
        })

    def logout(self, request: HttpRequest) -> HttpResponse:
        """Logout view."""
        return render(request, "accounts/logout.html", {})
    
class ExamplesView(View):
    def example_organization_members(self, request: HttpRequest) -> HttpResponse:
        """Example organization members view."""

        # Mock data for example organization members view
        user = UserProfile(username="example_user", email="user@example.com")
        organization_id = "example_org_id"
        organization = Organization(id=organization_id, name="Example Organization", email="org@example.com")
        members = [
            OrganizationMember(user=user, organization=organization, role="admin"),
            OrganizationMember(user=UserProfile(username="member1", email="member1@example.com"), organization=organization, role="member"),
        ]
        pending_invites = [
            PendingInvites(email="invitee@example.com", organization=organization),
        ]
        user_organizations = [
            organization,
            Organization(id="org2", name="Another Org", email="another@example.com"),
        ]
        is_admin = True

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

class ComponentsView(View):
    """Class-based view for components."""

    def components(self, request: HttpRequest) -> HttpResponse:
        """Components view."""
        return render(request, "components/components.html", {})

def google_verification(request: HttpRequest) -> HttpResponse:
    """Google verification view."""
    # This is a static HTML file for Google Search Console verification
    return render(request, "google_stuff/google0f33857d0e9df9a5.html", content_type="text/html")

def sitemap(request: HttpRequest) -> HttpResponse:
    """Sitemap view."""
    # This is a static XML file for sitemap
    return render(request, "google_stuff/sitemap.xml", content_type="application/xml")


# Create instances for URL routing
dashboard_view = DashboardView()
payment_view = PaymentView()
auth_view = AuthView()
components_view = ComponentsView()
examples_view = ExamplesView()