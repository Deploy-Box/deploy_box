from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.conf import settings
from accounts.forms import CustomUserCreationForm
from organizations.models import Organization, OrganizationMember
from projects.models import Project
from stacks.models import Stack
from organizations.forms import OrganizationCreateForm, OrganizationCreateFormWithMembers, OrganizationMemberForm

from core.decorators import oauth_required


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
    organizations = Organization.objects.filter(organizationmember__user = user)
    projects = Project.objects.filter(projectmember__user = user)
    return render(request, "dashboard.html", {'user': user, 'organizations': organizations, 'projects': projects})

@oauth_required()
def organization_dashboard(request: HttpRequest, organization_id: str) -> HttpResponse:
    user=request.user
    organization = Organization.objects.get(id=organization_id)
    members = OrganizationMember.objects.filter(organization=organization)
    return render(request, "organization_dashboard.html", {'user': user, 'organization': organization, 'members': members})

@oauth_required()
def project_dashboard(request: HttpRequest, organization_id: str, project_id: str) -> HttpResponse:
    user = request.user
    project = Project.objects.get(id=project_id)
    stacks = Stack.objects.filter(project_id=project_id)
    return render(request, "project_dashboard.html", {"organization_id": organization_id, "project": project, 'stacks': stacks})

@oauth_required()
def stack_dashboard(request: HttpRequest, organization_id: str, project_id: str, stack_id: str) -> HttpResponse:
    user = request.user
    stack = Stack.objects.get(id=stack_id)
    return render(request, "stack_dashboard.html", {"organization_id": organization_id, "project_id": project_id, "stack": stack})


def maintenance(request: HttpRequest) -> HttpResponse:
    return render(request, "maintenance.html", {})


# Authentication Routes
def login(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/login.html", {})


def signup(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/signup.html", {"form": CustomUserCreationForm})


def logout(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/logout.html", {})


# Payment Routes
STRIPE_PUBLISHABLE_KEY = settings.STRIPE.get("PUBLISHABLE_KEY", None)


@oauth_required()
def home_page_view(request: HttpRequest) -> HttpResponse:
    return render(request, "payments/home.html")


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
    return render(request, 'accounts/create_organization_form.html', {'form': form})
