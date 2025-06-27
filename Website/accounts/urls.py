from django.urls import path
from .views import SignupAPIView, OAuthPasswordLoginView, OAuthClientCredentialsView, M2MProtectedView, LogoutAPIView, ProfileAPIView, PasswordResetAPIView, PasswordResetConfirmAPIView

urlpatterns = [
    path("signup/", SignupAPIView.as_view(), name="api-signup"),
    path("logout/", LogoutAPIView.as_view(), name="api-logout"),
    path("login/", OAuthPasswordLoginView.as_view(), name="api-login"),
    path("oauth/m2m/", OAuthClientCredentialsView.as_view(), name="oauth-m2m"),
    path("m2m/protected/", M2MProtectedView.as_view(), name="m2m-protected"),
    path("profile/", ProfileAPIView.as_view(), name="api-profile"),
    path("password-reset/", PasswordResetAPIView.as_view(), name="api-password-reset"),
    path("password-reset/<str:uidb64>/<str:token>/", PasswordResetConfirmAPIView.as_view(), name="api-password-reset-confirm"),
]
