from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("stacks", views.stacks, name="stacks"),
    path("pricing", views.pricing, name="pricing"),
    path("contact", views.maintenance, name="maintenance"),
    path("profile", views.maintenance, name="maintenance"),
    path("user-dashboard", views.user_dashboard, name="user_dashboard")
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
