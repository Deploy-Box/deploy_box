from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("stacks/", views.stacks, name="stacks"),
    path("pricing/", views.pricing, name="pricing"),
    path("contact/", views.maintenance, name="maintenance"),
    path("profile/", views.maintenance, name="maintenance"),

    # Authentication Routes
    path("login/", auth_views.LoginView.as_view(template_name='accounts/login.html'), name="login"),
    path("signup/", views.signup, name="signup"),

    # Payment Routes
    path("payments/", views.home_page_view, name="payments_home"),
    path("payments/add-card/", views.add_card_view, name="add_card"),
    path("payments/success/", views.success_view, name="payments_success"),
    path("payments/cancelled/", views.cancelled_view, name="payments_cancelled"),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
