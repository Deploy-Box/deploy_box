from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from accounts.views import OAuthPasswordLoginView
from . import views

urlpatterns = [
    # Public pages
    path("", views.home, name="home"),
    path("stacks/", views.stacks, name="stacks"),
    path("stacks/mern/", views.mern_stack, name="mern_stack"),
    path("stacks/django/", views.django_stack, name="django_stack"),
    path("stacks/mean/", views.mean_stack, name="mean_stack"),
    path("stacks/lamp/", views.lamp_stack, name="lamp_stack"),
    path("stacks/mevn/", views.mevn_stack, name="mevn_stack"),
    path("pricing/", views.pricing, name="pricing"),
    path("contact/", views.maintenance, name="contact"),
    # User profile
    path("profile/", views.profile, name="profile"),
    # Dashboard
    path("dashboard/", views.dashboard_view.get, name="dashboard"),
    path(
        "dashboard/organizations/<str:organization_id>/",
        views.dashboard_view.organization_dashboard,
        name="organization_dashboard",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/billing/",
        views.dashboard_view.organization_billing,
        name="organization_billing",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/members/",
        views.dashboard_view.organization_members,
        name="organization_members",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/settings/",
        views.dashboard_view.organization_settings,
        name="organization_settings",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/projects/<str:project_id>/",
        views.dashboard_view.project_dashboard,
        name="project_dashboard",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/projects/<str:project_id>/settings/",
        views.dashboard_view.project_settings,
        name="project_settings",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/projects/<str:project_id>/stacks/<str:stack_id>/",
        views.dashboard_view.stack_dashboard,
        name="stack_dashboard",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/projects/<str:project_id>/stacks/<str:stack_id>/settings/",
        views.dashboard_view.stack_settings,
        name="stack_settings",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/projects/<str:project_id>/stacks/<str:stack_id>/environment-variables/",
        views.dashboard_view.environment_variables,
        name="environment_variables",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/add_org_member",
        views.dashboard_view.add_org_members,
        name="add_org_members",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/add_nonexistant_org_member",
        views.dashboard_view.add_nonexistant_org_members,
        name="add_nonexistant_org_members",
    ),
    # Authentication
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("signup/", views.auth_view.signup, name="signup"),
    path("password_reset/", views.auth_view.password_reset, name="password_reset"),
    path(
        "password_reset/confirm/<str:uidb64>/<str:token>/",
        views.auth_view.password_reset_confirm,
        name="password_reset_confirm",
    ),
    # Payment pages
    path("payments/<str:variant>", views.payment_view.home_page_view, name="payments_home"),
    path("payments/cards/add/", views.payment_view.add_card_view, name="card_add"),
    path("payments/checkout/success/", views.payment_view.success_view, name="checkout_success"),
    path(
        "payments/checkout/cancelled/", views.payment_view.cancelled_view, name="checkout_cancelled"
    ),
    path(
        "dashboard/create_organization_form/",
        views.dashboard_view.create_organization_form,
        name="create_organization_form",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/create_project_form",
        views.dashboard_view.create_project_form,
        name="create_project_form",
    ),
    path(
        "project-transfer/accept/<str:transfer_id>/",
        views.dashboard_view.project_transfer_accept,
        name="project_transfer_accept",
    ),
    path(
        "dashboard/transfers/",
        views.dashboard_view.transfer_invitations,
        name="transfer_invitations",
    ),
    path(
        "components/",
        views.components_view.components,
        name="components",
    ),
    path(
        "google0f33857d0e9df9a5.html", views.google_verification, name="google_verification"
    ),
    path(
        "sitemap.xml", views.sitemap, name="sitemap"
    ),
    path(
        "examples/organization_members/", views.examples_view.example_organization_members, name="example_organization_members"
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
