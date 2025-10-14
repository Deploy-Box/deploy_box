from django.urls import path
from .views import generate, revoke, rotate, increment_api_usage, generate_token

urlpatterns = [
    path("generate/", generate, name="api-generate"),
    path("revoke/", revoke, name="api-revoke"),
    path("rotate/", rotate, name="api-rotate"),
    path("increment_usage/", increment_api_usage, name="api-increment-usage"),
    path("generate_token/", generate_token, name="api-token"),
]