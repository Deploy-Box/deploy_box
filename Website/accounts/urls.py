from django.urls import path
from .views import (
    SignupAPIView, LogoutAPIView, ProfileAPIView, 
    DeleteAccountAPIView,
    WorkOSAuthInitiateView, WorkOSAuthCallbackView,
)

urlpatterns = [
    path("signup/", SignupAPIView.as_view(), name="api-signup"),
    path("logout/", LogoutAPIView.as_view(), name="api-logout"),
    path("profile/", ProfileAPIView.as_view(), name="api-profile"),
    path("delete-account/", DeleteAccountAPIView.as_view(), name="api-delete-account"),

    # WorkOS AuthKit SSO
    path("oauth/workos/", WorkOSAuthInitiateView.as_view(), name="workos-auth-initiate"),
    path("oauth/workos/callback/", WorkOSAuthCallbackView.as_view(), name="workos-auth-callback"),
]
