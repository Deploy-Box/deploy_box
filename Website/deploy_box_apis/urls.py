from django.urls import path
from .views import (
    generate, revoke, rotate, increment_api_usage, generate_token,
    generate_api_key, revoke_api_key, list_api_keys, validate_api_key,
)

urlpatterns = [
    path("generate/", generate, name="api-generate"),
    path("revoke/", revoke, name="api-revoke"),
    path("rotate/", rotate, name="api-rotate"),
    path("increment_usage/", increment_api_usage, name="api-increment-usage"),
    path("generate_token/", generate_token, name="api-token"),
    # Public API key management
    path("keys/generate/", generate_api_key, name="api-key-generate"),
    path("keys/revoke/", revoke_api_key, name="api-key-revoke"),
    path("keys/", list_api_keys, name="api-key-list"),
    path("keys/validate/", validate_api_key, name="api-key-validate"),
]