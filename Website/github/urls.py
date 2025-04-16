from django.urls import path
from . import views

urlpatterns = [
    # GitHub integration home
    path("", views.home, name="github_home"),

    # Authentication
    path("auth/login/", views.github_login, name="github_login"),
    path("auth/callback/", views.github_callback, name="github_callback"),
    path("auth/logout/", views.logout, name="github_logout"),

    # Repository management
    path("repositories/", views.list_repos, name="repository_list"),

    # Webhook management
    path("webhooks/create/", views.create_github_webhook, name="webhook_create"),
    path("webhooks/", views.github_webhook, name="webhook_handler"),
]
