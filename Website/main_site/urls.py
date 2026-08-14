from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
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
    path("stacks/mobile/", views.mobile_stack, name="mobile_stack"),
    path("stacks/llm/", views.llm_stack, name="llm_stack"),
    path("stacks/ai-data/", views.ai_data_stack, name="ai_data_stack"),
    path("stacks/computer-vision/", views.computer_vision_stack, name="computer_vision_stack"),
    path("stacks/image-generation/", views.image_generation_stack, name="image_generation_stack"),
    path("stacks/ai-agents/", views.ai_agents_stack, name="ai_agents_stack"),
    path("pricing/", views.pricing, name="pricing"),
    path("contact/", views.contact, name="contact"),
    # Documentation
    path("docs/", views.docs, name="docs"),
    path("docs/getting-started/", views.docs_getting_started, name="docs_getting_started"),
    path("docs/stacks/", views.docs_stacks, name="docs_stacks"),
    path("docs/organizations/", views.docs_organizations, name="docs_organizations"),
    path("docs/projects/", views.docs_projects, name="docs_projects"),
    path("docs/billing/", views.docs_billing, name="docs_billing"),
    path("docs/api/", views.docs_api, name="docs_api"),
    path("still-configuring/", views.still_configuring, name="still_configuring"),
    path("subdomain-not-found/", views.subdomain_not_found, name="subdomain_not_found"),
    path("marketplace/", include(("marketplace.urls", "marketplace"), namespace="marketplace")),
    # User profile
    path("profile/", views.profile, name="profile"),
    # Dashboard
    path("dashboard/", views.dashboard_view.get, name="dashboard"),
    path("dashboard/welcome/", views.dashboard_view.get, name="welcome"),
    path("dashboard/organizations/", views.dashboard_view.organization_select, name="organization_select"),
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
        "dashboard/organizations/<str:organization_id>/projects/<str:project_id>/marketplace/",
        views.dashboard_view.stack_marketplace,
        name="stack_marketplace",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/projects/<str:project_id>/api-marketplace/",
        views.dashboard_view.api_marketplace,
        name="api_marketplace",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/projects/<str:project_id>/marketplace/stack/<str:stack_id>/",
        views.dashboard_view.stack_details,
        name="stack_details",
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
        "dashboard/organizations/<str:organization_id>/projects/<str:project_id>/stacks/<str:stack_id>/environments/",
        views.dashboard_view.environments,
        name="environments",
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
    # Authentication - all auth flows go through WorkOS
    path(
        "login/",
        views.auth_view.login,
        name="login",
    ),
    path("signup/", views.auth_view.signup, name="signup"),
    # Payment pages
    path("payments/<str:variant>", views.payment_view.home_page_view, name="payments_home"),
    path("stacks-marketplace/", views.payment_view.stacks_marketplace_view, name="stacks_marketplace"),
    path("payments/cards/add/", views.payment_view.add_card_view, name="card_add"),
    path("payments/checkout/success/", views.payment_view.success_view, name="checkout_success"),
    path(
        "payments/checkout/cancelled/", views.payment_view.cancelled_view, name="checkout_cancelled"
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
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'favicon.ico')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
