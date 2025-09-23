from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views

# Create your views here.
urlpatterns = [
    path("developer/", views.developer, name="create_developer"),
    path("+", views.marketplace, name="marketplace")
]
