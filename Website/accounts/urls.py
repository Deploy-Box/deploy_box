from django.urls import path
from .views import SignupAPIView, OAuthPasswordLoginView, OAuthClientCredentialsView, M2MProtectedView

urlpatterns = [
    path("signup/", SignupAPIView.as_view(), name="signup"),
    path("login/", OAuthPasswordLoginView.as_view(), name="api-login"),
    path("oauth/m2m/", OAuthClientCredentialsView.as_view(), name="oauth-m2m"),
    path("m2m/protected/", M2MProtectedView.as_view(), name="m2m-protected"),
]
