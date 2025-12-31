from django.urls import path
from . import views

app_name = "marketplace"

urlpatterns = [
    path("", views.marketplace_home, name="home"),
    path("register/", views.register_developer, name="register"),
    path("profile/<str:profile_id>/", views.developer_detail, name="profile_detail"),
]
