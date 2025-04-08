from django.urls import path
from . import views

urlpatterns = [
    path("authorize/", views.oauth_authorize, name="oauth_authorize"),
    path("callback/", views.oauth_callback, name="oauth_callback"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup, name="signup"),
    path("logout/", views.logout_view, name="logout"),

    #organizations
    path("organizations/", views.get_organizations, name="organizations"),
    path("organizations/create-organization/", views.create_organization, name="create_organization"),
    path("organizations/update-organization/", views.update_organization, name="update_organization"),
    path("organizations/delete-organization/", views.delete_organization, name="delete_organization"),
    path("organizations/add-collaborator/", views.add_org_members, name="add_org_members"),  
    path("organizations/remove-collaborator/", views.remove_org_member, name="remove_org_member"),

    #projects  
    path("organizations/create-project/", views.create_project, name="create_project"),  
    path("organizations/update-project/", views.update_project, name="update_project"),  
    path("organizations/delete-project/", views.delete_project, name="delete_project"),  
    path("organizations/add-project-members/", views.add_project_members, name="add_project_members"),  
    path("organizations/delete-project-member/", views.delete_project_member, name="delete_project_member"),  
]
