from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
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
    path("dashboard/", views.dashboard, name="dashboard"),
    path(
        "dashboard/organizations/<str:organization_id>/",
        views.organization_dashboard,
        name="organization_dashboard",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/projects/<str:project_id>/",
        views.project_dashboard,
        name="project_dashboard",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/projects/<str:project_id>/stacks/<str:stack_id>/",
        views.stack_dashboard,
        name="stack_dashboard",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/add_org_member",
        views.add_org_members,
        name="add_org_members",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/add_nonexistant_org_member",
        views.add_nonexistant_org_members,
        name="add_nonexistant_org_members",
    ),
    # Authentication
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("signup/", views.signup, name="signup"),
    path("password_reset/", views.password_reset, name="password_reset"),
    path(
        "password_reset/confirm/<str:uidb64>/<str:token>/",
        views.password_reset_confirm,
        name="password_reset_confirm",
    ),
    # Payment pages
    path("payments/<str:variant>", views.home_page_view, name="payments_home"),
    path("payments/cards/add/", views.add_card_view, name="card_add"),
    path("payments/checkout/success/", views.success_view, name="checkout_success"),
    path(
        "payments/checkout/cancelled/", views.cancelled_view, name="checkout_cancelled"
    ),
    path(
        "dashboard/organizations/create_organization_form",
        views.create_organization_form,
        name="create_organization_form",
    ),
    path(
        "dashboard/organizations/<str:organization_id>/create_project_form",
        views.create_project_form,
        name="create_project_form",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
