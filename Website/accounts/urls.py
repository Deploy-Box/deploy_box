from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # Authentication endpoints
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    # OAuth endpoints
    path("oauth/authorize/", views.oauth_authorize, name="oauth_authorize"),
    path("oauth/callback/", views.oauth_callback, name="oauth_callback"),
    path("password-reset/", views.password_reset, name="password_reset"),
    path(
        "reset/<str:uidb64>/<str:token>/",
        views.password_reset_confirm,
        name="password_reset_confirm",
    ),
]
