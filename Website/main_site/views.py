from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.conf import settings
from django.contrib import messages
from accounts.forms import CustomUserCreationForm
from accounts.models import UserProfile
from organizations.models import Organization, OrganizationMember, PendingInvites
from organizations.forms import (
    OrganizationCreateFormWithMembers,
    OrganizationMemberForm,
    NonexistantOrganizationMemberForm,
)
from rest_framework.request import Request
from organizations.services import get_organizations
from projects.forms import ProjectCreateFormWithMembers, ProjectSettingsForm
from projects.models import Project, ProjectMember
from stacks.forms import EnvFileUploadForm, StackSettingsForm, EnvironmentVariablesForm
from stacks.models import PurchasableStack, StackGoogleCloudRun, Stack
from stacks.services import post_stack_env
from core.decorators import oauth_required
from django.views import View
from django.shortcuts import render
from typing import cast

import logging

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
            return redirect('main_site:organization_dashboard', organization_id=first_organization.id)
        else:
            return render(
                request,
                "dashboard/dashboard.html",
                {
                    "user": user,
                    "organizations": organizations,
                    "projects": projects,
                    "user_organizations": organizations,
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
            import stripe
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
        from stacks.models import StackDatabase
        from django.db.models import Sum
        from datetime import datetime, timedelta
        from django.utils import timezone
        from payments.models import usage_information, billing_history

        # Get all stacks for this organization's projects
        organization_projects = Project.objects.filter(organization=organization)
        organization_stacks = Stack.objects.filter(project__in=organization_projects)

        # Get current time in user's timezone (you can customize this)
        current_time = timezone.now()
        month_start = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Calculate usage metrics
        daily_usage = usage_information.get_total_current_usage_for_organization(organization)
        current_usage = usage_information.get_total_monthly_usage_for_organization(organization)
        projected_monthly_usage = current_usage * (30 / (current_time.day or 1))

        #get billing history for the organization
        billing_history_records = billing_history.get_billing_history_for_organization(organization)

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

        form = EnvFileUploadForm()

        # Get all organizations and projects for the user for dropdowns
        user_organizations = Organization.objects.filter(organizationmember__user=user)
        user_projects = Project.objects.filter(projectmember__user=user)
        user_stacks = Stack.objects.filter(project_id=project_id)
        # Get the current project for context
        project = Project.objects.get(id=project_id)

        return render(
            request,
            "dashboard/stack_dashboard.html",
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
    def create_organization_form(self, request: HttpRequest) -> HttpResponse:
        """Create organization form view."""
        form = OrganizationCreateFormWithMembers()
        return render(request, "accounts/create_organization_form.html", {"form": form})

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


class PaymentView(View):
    """Class-based view for all payment-related functionality."""

    STRIPE_PUBLISHABLE_KEY = settings.STRIPE.get("PUBLISHABLE_KEY", None)

    @oauth_required()
    def home_page_view(self, request: HttpRequest, variant: str) -> HttpResponse:
        """Payment home page view."""
        user_profile = cast(UserProfile, request.user)
        organizations = get_organizations(user_profile)
        projects = [
            project
            for organization in organizations
            for project in organization.get_projects()
        ]
        stack_options = PurchasableStack.objects.filter(variant=variant.lower())
        return render(
            request,
            "payments/home.html",
            {
                "organizations": organizations,
                "projects": projects,
                "stack_options": stack_options,
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
        invite_id = request.GET.get('invite')
        invite_data = None

        if invite_id:
            try:
                pending_invite = PendingInvites.objects.get(id=invite_id)
                invite_data = {
                    'invite_id': invite_id,
                    'organization_name': pending_invite.organization.name,
                    'organization_email': pending_invite.organization.email,
                    'invite_email': pending_invite.email
                }
            except PendingInvites.DoesNotExist:
                # Invalid invite ID - will be handled in template
                pass

        return render(request, "accounts/signup.html", {
            "form": CustomUserCreationForm,
            "invite_data": invite_data
        })

    def logout(self, request: HttpRequest) -> HttpResponse:
        """Logout view."""
        return render(request, "accounts/logout.html", {})

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
