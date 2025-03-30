from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.urls import include

urlpatterns = [
    path("protected-view", views.protected_view, name="protected_view"),
    path("me", views.me, name="me"),
    path("signup", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("callback/", views.oauth2_callback, name="callback"),
    path("update-user/", views.update_user, name="update_user"),
    path("password-reset", views.request_password_reset, name="password_reset_request"),
    path("password-reset/<uidb64>/<token>", views.reset_password, name="password_reset"),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('delete_user', views.delete_user, name='delete_user'),
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
]
