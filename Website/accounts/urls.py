from django.urls import path
from .views import SignupAPIView, OAuthPasswordLoginView, OAuthCallbackView

urlpatterns = [
    path("signup/", SignupAPIView.as_view(), name="api-signup"),
    path("login/", OAuthPasswordLoginView.as_view(), name="api-login"),
    path("oauth/callback/", OAuthCallbackView.as_view(), name="oauth-callback"),
]
