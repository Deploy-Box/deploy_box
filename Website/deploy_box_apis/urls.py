from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CredentialViewSet, APIKeyViewSet

router = DefaultRouter(trailing_slash=True)
router.register(r"credentials", CredentialViewSet, basename="credential")
router.register(r"keys", APIKeyViewSet, basename="api-key")

urlpatterns = [
    # Credential management (generate, revoke, rotate, token, usage)
    path("generate/", CredentialViewSet.as_view({"post": "generate"}), name="api-generate"),
    path("revoke/", CredentialViewSet.as_view({"post": "revoke"}), name="api-revoke"),
    path("rotate/", CredentialViewSet.as_view({"post": "rotate"}), name="api-rotate"),
    path("increment_usage/", CredentialViewSet.as_view({"post": "increment_usage"}), name="api-increment-usage"),
    path("generate_token/", CredentialViewSet.as_view({"post": "generate_token"}), name="api-token"),
    # Public API key management
    path("keys/generate/", APIKeyViewSet.as_view({"post": "generate_key"}), name="api-key-generate"),
    path("keys/revoke/", APIKeyViewSet.as_view({"post": "revoke_key"}), name="api-key-revoke"),
    path("keys/", APIKeyViewSet.as_view({"get": "list"}), name="api-key-list"),
    path("keys/validate/", APIKeyViewSet.as_view({"post": "validate_key"}), name="api-key-validate"),
]