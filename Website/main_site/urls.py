from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Public pages
    path("", views.home, name="home"),
    path("stacks/", views.stacks, name="stacks"),
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
    # Authentication
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("signup/", views.signup, name="signup"),
    # Payment pages
    path("payments/", views.home_page_view, name="payments_home"),
    path("payments/cards/add/", views.add_card_view, name="card_add"),
    path("payments/checkout/success/", views.success_view, name="checkout_success"),
    path(
        "payments/checkout/cancelled/", views.cancelled_view, name="checkout_cancelled"
    ),
    path("dashboard/organizations/create_organization_form", views.create_organization_form, name='create_organization_form'),
    path("dashboard/organizations/<str:organization_id>/create_project_form", views.create_project_form, name='create_project_form')
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
