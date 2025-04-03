from django.urls import path
from . import views

urlpatterns = [
    path("authorize/", views.oauth_authorize, name="oauth_authorize"),
    path("callback/", views.oauth_callback, name="oauth_callback"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("organizations/", views.get_organizations, name="organizations"),
    path("projects/", views.get_projects, name="projects"),    

]
