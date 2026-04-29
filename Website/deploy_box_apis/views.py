import json
import os

from django.db.models import OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from deploy_box_apis.models import API, APICredential, APIKey, APIUsage
from deploy_box_apis.serializers import (
    ProjectIDSerializer,
    APIKeyCreateSerializer,
    APIKeyRevokeSerializer,
    APIKeyValidateSerializer,
    IncrementUsageSerializer,
)
from deploy_box_apis import services
from deploy_box_apis.services import ServiceError
from typing import Any, Dict, List, Optional, TypedDict


def _error_response(exc: ServiceError) -> Response:
    """Convert a service-layer exception into a DRF Response."""
    return Response({"error": str(exc)}, status=exc.status_code)


class CredentialViewSet(ViewSet):
    """Manage OAuth client credentials for project APIs."""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="generate", url_name="generate")
    def generate(self, request):
        serializer = ProjectIDSerializer(data=request.POST or request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = services.generate_credential(serializer.validated_data["project_id"])
        except ServiceError as exc:
            return _error_response(exc)
        return Response(data)

    @action(detail=False, methods=["post"], url_path="revoke", url_name="revoke")
    def revoke(self, request):
        serializer = ProjectIDSerializer(data=request.POST or request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = services.revoke_credential(serializer.validated_data["project_id"])
        except ServiceError as exc:
            return _error_response(exc)
        return Response(data)

    @action(detail=False, methods=["post"], url_path="rotate", url_name="rotate")
    def rotate(self, request):
        serializer = ProjectIDSerializer(data=request.POST or request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = services.rotate_credential(serializer.validated_data["project_id"])
        except ServiceError as exc:
            return _error_response(exc)
        return Response(data)

    @action(detail=False, methods=["post"], url_path="generate_token", url_name="generate_token")
    def generate_token(self, request):
        serializer = ProjectIDSerializer(data=request.POST or request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = services.generate_token(serializer.validated_data["project_id"])
        except ServiceError as exc:
            return _error_response(exc)
        return Response(data)

    @action(detail=False, methods=["post"], url_path="increment_usage", url_name="increment_usage",
            permission_classes=[AllowAny])
    def increment_usage(self, request):
        raw_data = request.data.get("data", {})
        serializer = IncrementUsageSerializer(data=raw_data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = services.increment_usage(
                client_id=serializer.validated_data["client_id"],
                api_id=serializer.validated_data["api_id"],
            )
        except ServiceError as exc:
            return _error_response(exc)
        return Response(data)


class APIKeyViewSet(ViewSet):
    """Manage public API keys (Google-style)."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        project_id = request.GET.get("project_id")
        try:
            keys = services.list_api_keys(project_id)
        except ServiceError as exc:
            return _error_response(exc)
        return Response({"api_keys": keys})

    @action(detail=False, methods=["post"], url_path="generate", url_name="generate")
    def generate_key(self, request):
        serializer = APIKeyCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = services.create_api_key(
                project_id=serializer.validated_data["project_id"],
                name=serializer.validated_data.get("name", "Default"),
            )
        except ServiceError as exc:
            return _error_response(exc)
        return Response(data)

    @action(detail=False, methods=["post"], url_path="revoke", url_name="revoke")
    def revoke_key(self, request):
        serializer = APIKeyRevokeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = services.revoke_api_key(
                key_id=serializer.validated_data["key_id"],
                project_id=serializer.validated_data["project_id"],
            )
        except ServiceError as exc:
            return _error_response(exc)
        return Response(data)

    @action(detail=False, methods=["post"], url_path="validate", url_name="validate",
            permission_classes=[AllowAny])
    def validate_key(self, request):
        serializer = APIKeyValidateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = services.validate_api_key(serializer.validated_data["api_key"])
        except ServiceError as exc:
            return _error_response(exc)

        if not data.get("valid"):
            return Response(data, status=status.HTTP_404_NOT_FOUND)
        return Response(data)


# ── Helper used by main_site dashboard views ────────────────────────────────

class APIItem(TypedDict, total=False):
    id: int
    name: str
    description: str
    price_per_1000_requests: Any
    endpoint: str
    icon: str
    category: str
    popular: bool
    response_time: Any
    features: Any
    usage_count: int

class APIInfo(TypedDict):
    available_apis: List[APIItem]
    api_key: Optional[Dict[str, str]]
    base_url: Optional[str]

def get_project_api_info(project_id: str) -> APIInfo:
    usage_subq = (
        APIUsage.objects
        .filter(project_id=project_id, api_id=OuterRef("pk"))
        .values("api_id")
        .annotate(total=Sum("usage_count"))
        .values("total")[:1]
    )

    available_apis_qs = (
        API.objects
        .values(
            "id", "name", "description", "price_per_1000_requests",
            "endpoint", "icon", "category", "popular", "response_time", "features"
        )
        .annotate(usage_count=Coalesce(Subquery(usage_subq), Value(0)))
    )
    available_apis: List[APIItem] = list(available_apis_qs)

    cred = (
        APICredential.objects
        .filter(project_id=project_id)
        .only("client_id", "client_secret_hint")
        .first()
    )
    api_key: Optional[Dict[str, str]] = None
    if cred:
        api_key = {
            "client_id": cred.client_id,
            "client_secret": cred.client_secret,
            "client_secret_hint": cred.client_secret_hint,
        }

    base_url_env = os.getenv("DEPLOY_BOX_API_BASE_URL")
    base_url = base_url_env.rstrip("/") if base_url_env else None

    return {
        "available_apis": available_apis,
        "api_key": api_key,
        "base_url": base_url,
        "token_endpoint": base_url + "/oauth2/token" if base_url else None,
    }