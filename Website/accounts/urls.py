from django.urls import path
from .views import (
    SignupAPIView, OAuthClientCredentialsView, 
    M2MProtectedView, LogoutAPIView, ProfileAPIView, 
    DeleteAccountAPIView,
    WorkOSAuthInitiateView, WorkOSAuthCallbackView,
)

urlpatterns = [
    path("signup/", SignupAPIView.as_view(), name="api-signup"),
    path("logout/", LogoutAPIView.as_view(), name="api-logout"),
    path("oauth/m2m/", OAuthClientCredentialsView.as_view(), name="oauth-m2m"),
    path("m2m/protected/", M2MProtectedView.as_view(), name="m2m-protected"),
    path("profile/", ProfileAPIView.as_view(), name="api-profile"),
    path("delete-account/", DeleteAccountAPIView.as_view(), name="api-delete-account"),

    # WorkOS AuthKit SSO
    path("oauth/workos/", WorkOSAuthInitiateView.as_view(), name="workos-auth-initiate"),
    path("oauth/workos/callback/", WorkOSAuthCallbackView.as_view(), name="workos-auth-callback"),
]
