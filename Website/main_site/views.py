from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.conf import settings
from accounts.forms import CustomUserCreationForm
from organizations.models import Organization, OrganizationMember
from projects.models import Project
from stacks.models import Stack
from organizations.forms import (
    OrganizationCreateFormWithMembers,
    OrganizationMemberForm,
    NonexistantOrganizationMemberForm,
)
from organizations.services import get_organizations
from projects.forms import ProjectCreateFormWithMembers
from stacks.forms import EnvFileUploadForm
from stacks.models import PurchasableStack, StackGoogleCloudRun

from core.decorators import oauth_required, AuthHttpRequest


# Basic Routes
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "home.html", {})


def stacks(request: HttpRequest) -> HttpResponse:
    return render(request, "stacks.html", {})


def pricing(request: HttpRequest) -> HttpResponse:
    return render(request, "pricing.html", {})


def profile(request: HttpRequest) -> HttpResponse:
    return render(request, "profile.html", {})


@oauth_required()
def dashboard(request: HttpRequest) -> HttpResponse:
    user = request.user
    organizations = Organization.objects.filter(organizationmember__user=user)
    projects = Project.objects.filter(projectmember__user=user)
    return render(
        request,
        "dashboard/base_dashboard.html",
        {"user": user, "organizations": organizations, "projects": projects},
    )


@oauth_required()
def organization_dashboard(request: HttpRequest, organization_id: str) -> HttpResponse:
    user = request.user
    organization = Organization.objects.get(id=organization_id)
    members = OrganizationMember.objects.filter(organization=organization)
    projects = Project.objects.filter(organization_id=organization_id)
    is_admin = OrganizationMember.objects.filter(
        organization=organization, user=user, role="admin"
    ).exists()
    return render(
        request,
        "dashboard/organization_dashboard.html",
        {
            "user": user,
            "organization": organization,
            "members": members,
            "is_admin": is_admin,
            "projects": projects,
        },
    )


@oauth_required()
def add_org_members(request: HttpRequest, organization_id: str) -> HttpResponse:
    user = request.user
    organization = Organization.objects.get(id=organization_id)
    form = OrganizationMemberForm()
    return render(
        request,
        "accounts/invite_org_member.html",
        {"organization": organization, "user": user, "form": form},
    )


def add_nonexistant_org_members(
    request: HttpRequest, organization_id: str
) -> HttpResponse:
    user = request.user
    organization = Organization.objects.get(id=organization_id)
    form = NonexistantOrganizationMemberForm()
    return render(
        request,
        "accounts/invite_nonexistant_org_member.html",
        {"organization": organization, "user": user, "form": form},
    )


@oauth_required()
def project_dashboard(
    request: HttpRequest, organization_id: str, project_id: str
) -> HttpResponse:
    user = request.user
    project = Project.objects.get(id=project_id)
    stacks = Stack.objects.filter(project_id=project_id)
    return render(
        request,
        "dashboard/project_dashboard.html",
        {"organization_id": organization_id, "project": project, "stacks": stacks},
    )


@oauth_required()
def stack_dashboard(
    request: AuthHttpRequest, organization_id: str, project_id: str, stack_id: str
) -> HttpResponse:
    # TODO: Check if user is a member of the project
    stack = Stack.objects.get(id=stack_id)
    stack_google_cloud_run = StackGoogleCloudRun.objects.filter(stack=stack).first()
    print(f"Stack: {stack}")
    print(f"Stack Google Cloud Run: {stack_google_cloud_run}")
    return render(
        request,
        "dashboard/stack_dashboard.html",
        {
            "organization_id": organization_id,
            "project_id": project_id,
            "stack": stack,
            "stack_google_cloud_run": stack_google_cloud_run,
        },
    )

    form = EnvFileUploadForm()
    return render(
        request,
        "dashboard/stack_dashboard.html",
        {
            "organization_id": organization_id,
            "project_id": project_id,
            "stack": stack,
            "form": form,
            "stack_google_cloud_run": stack_google_cloud_run,
        },
    )


def maintenance(request: HttpRequest) -> HttpResponse:
    return render(request, "maintenance.html", {})


# Authentication Routes
def login(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/login.html", {})


def password_reset(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/password_reset.html", {})


def password_reset_confirm(
    request: HttpRequest, uidb64: str, token: str
) -> HttpResponse:
    return render(
        request,
        "accounts/password_reset_confirm.html",
        {"uidb64": uidb64, "token": token},
    )


def signup(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/signup.html", {"form": CustomUserCreationForm})


def logout(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/logout.html", {})


# Payment Routes
STRIPE_PUBLISHABLE_KEY = settings.STRIPE.get("PUBLISHABLE_KEY", None)


@oauth_required()
def home_page_view(request: AuthHttpRequest, variant: str) -> HttpResponse:
    user = request.auth_user
    organizations = get_organizations(user)
    projects = [
        project
        for organization in organizations
        for project in organization.get_projects()
    ]
    stack_options = PurchasableStack.objects.filter(variant=variant)
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
def add_card_view(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "payments/add-card.html",
        {"stripe_publishable_key": STRIPE_PUBLISHABLE_KEY},
    )


@oauth_required()
def success_view(request: HttpRequest) -> HttpResponse:
    return render(request, "payments/success.html")


@oauth_required()
def cancelled_view(request: HttpRequest) -> HttpResponse:
    return render(request, "payments/cancelled.html")


@oauth_required()
def create_organization_form(request: HttpRequest) -> HttpResponse:
    form = OrganizationCreateFormWithMembers()
    return render(request, "accounts/create_organization_form.html", {"form": form})


@oauth_required()
def create_project_form(request: HttpRequest, organization_id: str) -> HttpResponse:
    form = ProjectCreateFormWithMembers()
    return render(
        request,
        "accounts/create_project_form.html",
        {"form": form, "organization_id": organization_id},
    )
