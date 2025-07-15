from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path("auth/login/", views.login, name="login"),
    path("auth/callback/", views.callback, name="callback"),
    path("auth/logout/", views.logout, name="logout"),
    # Repository management
    path("repositories/", views.list_repos, name="repository_list"),
    path("repositories/json/", views.get_repos_json, name="repository_list_json"),
    # Webhook management
    path("webhook/create/", views.create_github_webhook, name="create_webhook"),
    path("webhook/disconnect/", views.disconnect_github_webhook, name="disconnect_webhook"),
    path("webhook/status/", views.get_webhook_status, name="webhook_status"),
    path("webhook/", views.github_webhook, name="webhook_handler"),

]
