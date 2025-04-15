from django.urls import path
from . import views

urlpatterns = [
    # Authentication endpoints
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    # OAuth endpoints
    path("oauth/authorize/", views.oauth_authorize, name="oauth_authorize"),
    path("oauth/callback/", views.oauth_callback, name="oauth_callback"),
    # Organization management
    path("organizations/", views.get_organizations, name="organizations_list"),
    path(
        "organizations/create/", views.create_organization, name="organization_create"
    ),
    path(
        "organizations/<str:org_id>/update/",
        views.update_organization,
        name="organization_update",
    ),
    path(
        "organizations/<str:org_id>/delete/",
        views.delete_organization,
        name="organization_delete",
    ),
    path(
        "organizations/<str:org_id>/members/add/",
        views.add_org_members,
        name="organization_member_add",
    ),
    path(
        "organizations/<str:org_id>/members/<str:member_id>/remove/",
        views.remove_org_member,
        name="organization_member_remove",
    ),
    # Project management
    path(
        "organizations/<str:org_id>/projects/create/",
        views.create_project,
        name="project_create",
    ),
    path(
        "organizations/<str:org_id>/projects/<str:project_id>/update/",
        views.update_project,
        name="project_update",
    ),
    path(
        "organizations/<str:org_id>/projects/<str:project_id>/delete/",
        views.delete_project,
        name="project_delete",
    ),
    path(
        "organizations/<str:org_id>/projects/<str:project_id>/members/add/",
        views.add_project_members,
        name="project_member_add",
    ),
    path(
        "organizations/<str:org_id>/projects/<str:project_id>/members/<str:member_id>/remove/",
        views.delete_project_member,
        name="project_member_remove",
    ),
]
