from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.conf import settings
from django.contrib import messages
from django.views import View
from typing import cast
import logging
import calendar
import stripe

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
from stacks.models import PurchasableStack, StackGoogleCloudRun, Stack
from stacks.services import post_stack_env
from core.decorators import oauth_required
from core.utils.DeployBoxIAC.main import DeployBoxIAC

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

        # Get usage data for the organization
        from django.utils import timezone
        from payments.models import billing_history

        # Get all stacks for this organization's projects
        organization_projects = Project.objects.filter(organization=organization)
        organization_stacks = Stack.objects.filter(project__in=organization_projects)

        # Get current time in user's timezone (you can customize this)
        current_time = timezone.now()
        month_start = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        num_days_in_month = calendar.monthrange(current_time.year, current_time.month)[1]

        # Calculate usage metrics
        billing_info = DeployBoxIAC().get_billing_info()

        for info in billing_info.values():
            if info.get("cost") < current_time.day / num_days_in_month:
                info["cost"] = current_time.day / num_days_in_month

        current_usage = sum(billing_info.get(stack.id, {}).get("cost", 0.00) for stack in organization_stacks)
        daily_usage = current_usage / (current_time.day or 1)
        projected_monthly_usage = current_usage * (num_days_in_month / (current_time.day or 1))

        #get billing history for the organization
        billing_history_records = billing_history.get_billing_history_for_organization(organization)

        # Check if the billing history stripe inovice statuses have changed
        for record in billing_history_records:
            if record.status.upper() == "PAID":
                continue
            
            if record.stripe_invoice_id:
                try:
                    invoice = stripe.Invoice.retrieve(record.stripe_invoice_id)
                    if invoice.status != record.status:
                        record.status = invoice.status
                        record.save()
                except Exception as e:
                    logger.error(f"Error retrieving invoice: {e}")
                    record.status = "failed"
                    record.save()
                    continue

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

        stacks = Stack.objects.filter(project_id=project_id)

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
        stack = Stack.objects.get(id=stack_id)

        # Handle stack deletion
        if request.method == 'POST' and request.POST.get('action') == 'delete':
            # Check if user has permission to delete the stack (project admin)
            project = Project.objects.get(id=project_id)
            project_member = ProjectMember.objects.filter(user=user, project=project, role='admin').first()
            if project_member:
                stack.delete()
                return redirect('main_site:project_dashboard', organization_id=organization_id, project_id=project_id)
            else:
                # User doesn't have permission to delete
                pass  # Could add error handling here

        stack_google_cloud_runs = list(StackGoogleCloudRun.objects.filter(stack=stack))

        for stack_google_cloud_run in stack_google_cloud_runs:
            if not stack_google_cloud_run.url:
                pass
                # gcp_utils = GCPUtils()
                # stack_google_cloud_run.url = gcp_utils.get_service_url(
                #     stack_google_cloud_run.id
                # )
                # stack_google_cloud_run.save()

            if stack_google_cloud_run.state == "STARTING":
                pass
                # gcp_utils = GCPUtils()
                # stack_google_cloud_run.state = gcp_utils.get_build_status(
                #     stack_google_cloud_run.build_status_url
                # )
                # stack_google_cloud_run.save()

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
        project = Project.objects.get(id=project_id)

        # Determine template based on stack type
        stack_type = stack.purchased_stack.type.lower()
        if stack_type == "mern":
            template_name = "dashboard/mern_stack_dashboard.html"
        elif stack_type == "django":
            template_name = "dashboard/django_stack_dashboard.html"
        else:
            template_name = "dashboard/stack_dashboard.html"

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
                "stack_google_cloud_runs": stack_google_cloud_runs,
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

        # Get actual purchasable stacks from database
        from stacks.models import PurchasableStack
        from django.conf import settings
        
        stripe.api_key = settings.STRIPE.get("SECRET_KEY")
        
        # Fetch all purchasable stacks and their pricing
        purchasable_stacks = []
        try:
            db_stacks = PurchasableStack.objects.all()
            
            for stack in db_stacks:
                try:
                    # Get price information from Stripe
                    price = stripe.Price.retrieve(stack.price_id)
                    price_amount = price.unit_amount / 100 if price.unit_amount else 0  # Convert cents to dollars
                    
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
                    
                    # Generate features based on stack type and variant
                    features = self._generate_stack_features(stack.type, stack.variant)
                    
                    purchasable_stacks.append({
                        'id': str(stack.id),
                        'name': stack.name,
                        'type': stack.type,
                        'variant': stack.variant,
                        'description': stack.description,
                        'price': price_amount,
                        'features': features,
                        'icon': icon_map.get(stack.type, '📦'),
                        'color': color_map.get(stack.variant, 'emerald'),
                        'popular': False,  # Could be determined by sales volume or admin setting
                        'is_from_database': True  # Flag to identify database entries
                    })
                except stripe.error.StripeError as e: # type: ignore[attr-defined]
                    # Log error but continue with other stacks
                    logger.error(f"Error fetching price for stack {stack.id}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error fetching purchasable stacks: {e}")

        # Hardcoded stack examples for the marketplace (existing mock data)
        mock_stacks = [
            {
                'id': 'mern-basic',
                'name': 'MERN Stack - Basic',
                'type': 'MERN',
                'variant': 'Basic',
                'description': 'Full-stack JavaScript solution with MongoDB, Express.js, React, and Node.js',
                'price': 29.99,
                'features': [
                    'MongoDB Database',
                    'Express.js Backend API',
                    'React Frontend',
                    'Node.js Runtime',
                    'Docker Containerization',
                    'Auto-deployment'
                ],
                'icon': '⚛️',
                'color': 'emerald',
                'popular': False,
                'is_from_database': False
            },
            {
                'id': 'mern-premium',
                'name': 'MERN Stack - Premium',
                'type': 'MERN',
                'variant': 'Premium',
                'description': 'Advanced MERN stack with additional features and optimizations',
                'price': 49.99,
                'features': [
                    'Everything in Basic',
                    'Redis Caching',
                    'Advanced Security',
                    'Performance Monitoring',
                    'CI/CD Pipeline',
                    'Priority Support'
                ],
                'icon': '⚛️',
                'color': 'amber',
                'popular': True,
                'is_from_database': False
            },
            {
                'id': 'django-basic',
                'name': 'Django Stack - Basic',
                'type': 'Django',
                'variant': 'Basic',
                'description': 'Python web framework with PostgreSQL and modern frontend',
                'price': 34.99,
                'features': [
                    'Django Backend',
                    'PostgreSQL Database',
                    'React Frontend',
                    'Docker Containerization',
                    'Admin Interface',
                    'Auto-deployment'
                ],
                'icon': '🐍',
                'color': 'emerald',
                'popular': False,
                'is_from_database': False
            },
            {
                'id': 'django-premium',
                'name': 'Django Stack - Premium',
                'type': 'Django',
                'variant': 'Premium',
                'description': 'Enterprise-grade Django stack with advanced features',
                'price': 59.99,
                'features': [
                    'Everything in Basic',
                    'Redis Caching',
                    'Celery Task Queue',
                    'Advanced Security',
                    'Performance Monitoring',
                    'Priority Support'
                ],
                'icon': '🐍',
                'color': 'amber',
                'popular': False,
                'is_from_database': False
            },
            {
                'id': 'mean-basic',
                'name': 'MEAN Stack - Basic',
                'type': 'MEAN',
                'variant': 'Basic',
                'description': 'JavaScript full-stack with MongoDB, Express.js, Angular, and Node.js',
                'price': 39.99,
                'features': [
                    'MongoDB Database',
                    'Express.js Backend API',
                    'Angular Frontend',
                    'Node.js Runtime',
                    'Docker Containerization',
                    'Auto-deployment'
                ],
                'icon': '🅰️',
                'color': 'emerald',
                'popular': False,
                'is_from_database': False
            },
            {
                'id': 'mean-premium',
                'name': 'MEAN Stack - Premium',
                'type': 'MEAN',
                'variant': 'Premium',
                'description': 'Advanced MEAN stack with enterprise features',
                'price': 69.99,
                'features': [
                    'Everything in Basic',
                    'Redis Caching',
                    'Advanced Security',
                    'Performance Monitoring',
                    'CI/CD Pipeline',
                    'Priority Support'
                ],
                'icon': '🅰️',
                'color': 'amber',
                'popular': False,
                'is_from_database': False
            },
            {
                'id': 'lamp-basic',
                'name': 'LAMP Stack - Basic',
                'type': 'LAMP',
                'variant': 'Basic',
                'description': 'Classic web stack with Linux, Apache, MySQL, and PHP',
                'price': 24.99,
                'features': [
                    'Apache Web Server',
                    'MySQL Database',
                    'PHP Backend',
                    'Docker Containerization',
                    'Basic Security',
                    'Auto-deployment'
                ],
                'icon': '🐘',
                'color': 'emerald',
                'popular': False,
                'is_from_database': False
            },
            {
                'id': 'lamp-premium',
                'name': 'LAMP Stack - Premium',
                'type': 'LAMP',
                'variant': 'Premium',
                'description': 'Enhanced LAMP stack with modern features',
                'price': 44.99,
                'features': [
                    'Everything in Basic',
                    'Redis Caching',
                    'Advanced Security',
                    'Performance Monitoring',
                    'SSL Certificate',
                    'Priority Support'
                ],
                'icon': '🐘',
                'color': 'amber',
                'popular': False,
                'is_from_database': False
            },
            {
                'id': 'mern-pro',
                'name': 'MERN Stack - Pro',
                'type': 'MERN',
                'variant': 'Pro',
                'description': 'Enterprise-grade MERN stack with advanced features and scalability',
                'price': 79.99,
                'features': [
                    'Everything in Premium',
                    'Microservices Architecture',
                    'Advanced Caching (Redis + Memcached)',
                    'Load Balancing',
                    'Auto-scaling Infrastructure',
                    '24/7 Priority Support',
                    'Custom Domain Setup',
                    'Advanced Analytics'
                ],
                'icon': '⚛️',
                'color': 'purple',
                'popular': False,
                'is_from_database': False
            },
            {
                'id': 'django-pro',
                'name': 'Django Stack - Pro',
                'type': 'Django',
                'variant': 'Pro',
                'description': 'Enterprise Django stack with microservices and advanced features',
                'price': 89.99,
                'features': [
                    'Everything in Premium',
                    'Microservices Architecture',
                    'Advanced Caching (Redis + Memcached)',
                    'Load Balancing',
                    'Auto-scaling Infrastructure',
                    '24/7 Priority Support',
                    'Custom Domain Setup',
                    'Advanced Analytics'
                ],
                'icon': '🐍',
                'color': 'purple',
                'popular': False,
                'is_from_database': False
            },
            {
                'id': 'mean-pro',
                'name': 'MEAN Stack - Pro',
                'type': 'MEAN',
                'variant': 'Pro',
                'description': 'Enterprise MEAN stack with advanced features and scalability',
                'price': 99.99,
                'features': [
                    'Everything in Premium',
                    'Microservices Architecture',
                    'Advanced Caching (Redis + Memcached)',
                    'Load Balancing',
                    'Auto-scaling Infrastructure',
                    '24/7 Priority Support',
                    'Custom Domain Setup',
                    'Advanced Analytics'
                ],
                'icon': '🅰️',
                'color': 'purple',
                'popular': False,
                'is_from_database': False
            },
            {
                'id': 'lamp-pro',
                'name': 'LAMP Stack - Pro',
                'type': 'LAMP',
                'variant': 'Pro',
                'description': 'Enterprise LAMP stack with advanced features and scalability',
                'price': 69.99,
                'features': [
                    'Everything in Premium',
                    'Microservices Architecture',
                    'Advanced Caching (Redis + Memcached)',
                    'Load Balancing',
                    'Auto-scaling Infrastructure',
                    '24/7 Priority Support',
                    'Custom Domain Setup',
                    'Advanced Analytics'
                ],
                'icon': '🐘',
                'color': 'purple',
                'popular': False,
                'is_from_database': False
            }
        ]

        # Combine database stacks and mock stacks
        available_stacks = purchasable_stacks

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
                "available_stacks": available_stacks,
                "user": user,
                "user_organizations": user_organizations,
                "user_projects": user_projects,
                "user_stacks": user_stacks,
                "current_organization_id": organization_id,
                "current_project_id": project_id,
                "current_stack_id": "",
            },
        )

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
        
        if variant.upper() == 'BASIC':
            return base_features.get(stack_type, ['Basic features'])
        elif variant.upper() == 'PREMIUM':
            return premium_features.get(stack_type, ['Premium features'])
        elif variant.upper() == 'PRO':
            return pro_features.get(stack_type, ['Pro features'])
        else:
            return base_features.get(stack_type, ['Basic features'])

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

        # Mock API data for the marketplace
        available_apis = [
            {
                'id': 'geolocation-basic',
                'name': 'Geolocation API',
                'category': 'Location',
                'tier': 'Basic',
                'description': 'Get precise location data including coordinates, country, city, and timezone information',
                'price': 9.99,
                'features': [
                    'IP-based geolocation',
                    'Country and city detection',
                    'Timezone information',
                    '1,000 requests/month',
                    'JSON response format',
                    'Basic documentation'
                ],
                'icon': '🌍',
                'color': 'emerald',
                'popular': True,
                'endpoint': 'https://api.example.com/geolocation/v1',
                'response_time': '< 100ms'
            },
            {
                'id': 'weather-basic',
                'name': 'Weather API',
                'category': 'Weather',
                'tier': 'Basic',
                'description': 'Real-time weather data with current conditions and 5-day forecasts',
                'price': 14.99,
                'features': [
                    'Current weather conditions',
                    '5-day weather forecast',
                    'Temperature, humidity, wind data',
                    '2,000 requests/month',
                    'Multiple units support',
                    'Basic weather alerts'
                ],
                'icon': '🌤️',
                'color': 'emerald',
                'popular': True,
                'endpoint': 'https://api.example.com/weather/v1',
                'response_time': '< 200ms'
            },
            {
                'id': 'geolocation-premium',
                'name': 'Geolocation API - Premium',
                'category': 'Location',
                'tier': 'Premium',
                'description': 'Advanced geolocation with enhanced accuracy and additional data points',
                'price': 24.99,
                'features': [
                    'Everything in Basic',
                    'Enhanced accuracy',
                    'ISP and organization data',
                    '10,000 requests/month',
                    'Bulk geolocation',
                    'Advanced analytics',
                    'Priority support'
                ],
                'icon': '🌍',
                'color': 'amber',
                'popular': False,
                'endpoint': 'https://api.example.com/geolocation/v2',
                'response_time': '< 50ms'
            },
            {
                'id': 'weather-premium',
                'name': 'Weather API - Premium',
                'category': 'Weather',
                'tier': 'Premium',
                'description': 'Comprehensive weather data with extended forecasts and historical data',
                'price': 34.99,
                'features': [
                    'Everything in Basic',
                    'Extended 10-day forecast',
                    'Historical weather data',
                    '20,000 requests/month',
                    'Weather maps and radar',
                    'Severe weather alerts',
                    'Priority support'
                ],
                'icon': '🌤️',
                'color': 'amber',
                'popular': False,
                'endpoint': 'https://api.example.com/weather/v2',
                'response_time': '< 150ms'
            },
            {
                'id': 'currency-basic',
                'name': 'Currency Exchange API',
                'category': 'Finance',
                'tier': 'Basic',
                'description': 'Real-time currency exchange rates and conversion tools',
                'price': 12.99,
                'features': [
                    '170+ currency pairs',
                    'Real-time exchange rates',
                    'Historical rates',
                    '1,500 requests/month',
                    'JSON and XML formats',
                    'Basic conversion tools'
                ],
                'icon': '💰',
                'color': 'emerald',
                'popular': False,
                'endpoint': 'https://api.example.com/currency/v1',
                'response_time': '< 100ms'
            },
            {
                'id': 'email-validation-basic',
                'name': 'Email Validation API',
                'category': 'Validation',
                'tier': 'Basic',
                'description': 'Validate email addresses and check deliverability',
                'price': 7.99,
                'features': [
                    'Email format validation',
                    'Domain verification',
                    'Disposable email detection',
                    '2,500 requests/month',
                    'Bulk validation',
                    'Detailed response codes'
                ],
                'icon': '📧',
                'color': 'emerald',
                'popular': False,
                'endpoint': 'https://api.example.com/email/v1',
                'response_time': '< 80ms'
            },
            {
                'id': 'geolocation-pro',
                'name': 'Geolocation API - Pro',
                'category': 'Location',
                'tier': 'Pro',
                'description': 'Enterprise-grade geolocation with maximum accuracy and unlimited requests',
                'price': 49.99,
                'features': [
                    'Everything in Premium',
                    'Maximum accuracy',
                    'Unlimited requests',
                    'Custom data fields',
                    'White-label solution',
                    '24/7 priority support',
                    'SLA guarantee',
                    'Custom integrations'
                ],
                'icon': '🌍',
                'color': 'purple',
                'popular': False,
                'endpoint': 'https://api.example.com/geolocation/v3',
                'response_time': '< 25ms'
            },
            {
                'id': 'weather-pro',
                'name': 'Weather API - Pro',
                'category': 'Weather',
                'tier': 'Pro',
                'description': 'Enterprise weather solution with unlimited access and advanced features',
                'price': 69.99,
                'features': [
                    'Everything in Premium',
                    'Unlimited requests',
                    '30-day extended forecast',
                    'Weather modeling data',
                    'Custom weather alerts',
                    '24/7 priority support',
                    'SLA guarantee',
                    'Custom integrations'
                ],
                'icon': '🌤️',
                'color': 'purple',
                'popular': False,
                'endpoint': 'https://api.example.com/weather/v3',
                'response_time': '< 100ms'
            },
            {
                'id': 'ai-translation-basic',
                'name': 'AI Translation API',
                'category': 'AI',
                'tier': 'Basic',
                'description': 'Neural machine translation supporting 100+ languages',
                'price': 19.99,
                'features': [
                    '100+ language pairs',
                    'Neural translation',
                    'Context-aware translation',
                    '1,000 requests/month',
                    'Text and document translation',
                    'Basic language detection'
                ],
                'icon': '🤖',
                'color': 'emerald',
                'popular': False,
                'endpoint': 'https://api.example.com/translation/v1',
                'response_time': '< 500ms'
            },
            {
                'id': 'image-processing-basic',
                'name': 'Image Processing API',
                'category': 'Media',
                'tier': 'Basic',
                'description': 'AI-powered image processing, resizing, and optimization',
                'price': 16.99,
                'features': [
                    'Image resizing and cropping',
                    'Format conversion',
                    'Compression optimization',
                    '500 requests/month',
                    'Multiple output formats',
                    'Basic filters and effects'
                ],
                'icon': '🖼️',
                'color': 'emerald',
                'popular': False,
                'endpoint': 'https://api.example.com/image/v1',
                'response_time': '< 2s'
            }
        ]

        # Get all organizations and projects for the user for dropdowns
        user_organizations = Organization.objects.filter(organizationmember__user=user)
        user_projects = Project.objects.filter(projectmember__user=user)
        user_stacks = Stack.objects.filter(project__projectmember__user=user)
        
        return render(
            request,
            "dashboard/api_marketplace.html",
            {
                "organization": organization,
                "project": project,
                "available_apis": available_apis,
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
        
        for stack in db_stacks:
            try:
                # Get price information from Stripe
                price = stripe.Price.retrieve(stack.price_id)
                price_amount = price.unit_amount / 100 if price.unit_amount else 0  # Convert cents to dollars
                
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
                
                # Generate features based on stack type and variant
                features = self._generate_stack_features(stack.type, stack.variant)
                
                stack_options.append({
                    'id': str(stack.id),
                    'name': stack.name,
                    'type': stack.type,
                    'variant': stack.variant,
                    'description': stack.description,
                    'price': price_amount,
                    'features': features,
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