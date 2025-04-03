from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("stacks/", views.stacks, name="stacks"),
    path("pricing/", views.pricing, name="pricing"),
    path("contact/", views.maintenance, name="maintenance"),
    path("profile/", views.profile, name="maintenance"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/org/<str:organization_id>/", views.organization_dashboard, name="organization_dashboard"),
    path("dashboard/org/<str:organization_id>/proj/<str:project_id>/", views.project_dashboard, name="project_dashboard"),
    path("dashboard/org/<str:organization_id>/proj/<str:project_id>/stack/<str:stack_id>", views.stack_dashboard, name="stack_dashboard"),
    # Authentication Routes
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path("signup/", views.signup, name="signup"),
    # Payment Routes
    path("payments/", views.home_page_view, name="payments_home"),
    path("payments/add-card/", views.add_card_view, name="add_card"),
    path("payments/success/", views.success_view, name="payments_success"),
    path("payments/cancelled/", views.cancelled_view, name="payments_cancelled"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
