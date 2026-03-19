import json
from django.http import JsonResponse, HttpResponse
from rest_framework import status, filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from core.utils.webhook_auth import verify_iac_webhook_signature
from stacks.models import Stack, PurchasableStack
from stacks.serializers import StackSerializer
from stacks.services import (
    ServiceError,
    ValidationError,
    NotFoundError,
    create_stack,
    delete_stack,
    trigger_iac_update,
    bulk_update_resources,
    get_traefik_config,
    download_stack_source,
    upload_source_code,
)


def _error_response(exc: ServiceError) -> Response:
    """Convert a service-layer exception into a DRF Response."""
    return Response({"error": str(exc)}, status=exc.status_code)


class StackViewSet(viewsets.ModelViewSet):
    queryset = Stack.objects.exclude(status="Deleted")
    serializer_class = StackSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]

    # Actions that the IAC container-app calls back into, authenticated via
    # HMAC-SHA256 shared secret (see SEC-2).
    WEBHOOK_ACTIONS = ("bulk_update_resources_action", "partial_update")

    def get_permissions(self):
        if getattr(self, 'action', None) in self.WEBHOOK_ACTIONS:
            return [AllowAny()]
        return super().get_permissions()

    def get_authenticators(self):
        # Skip DRF authentication for webhook actions — they are verified via
        # HMAC signature in initialize_request / initial() instead.
        if getattr(self, 'action', None) in self.WEBHOOK_ACTIONS:
            return []
        return super().get_authenticators()

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if getattr(self, 'action', None) in self.WEBHOOK_ACTIONS:
            verify_iac_webhook_signature(request)

    # ----- CREATE --------------------------------------------------------
    def create(self, request):
        try:
            data = create_stack(
                project_id=request.data.get("project_id"),
                purchasable_stack_id=request.data.get("purchasable_stack_id"),
            )
        except ServiceError as exc:
            return _error_response(exc)

        return Response(data, status=status.HTTP_201_CREATED)

    # ----- PARTIAL UPDATE ------------------------------------------------
    def partial_update(self, request, pk=None):
        if not pk:
            return Response(
                {"error": "Stack ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            stack = Stack.objects.get(pk=pk)
        except Stack.DoesNotExist:
            return Response({"error": "Stack not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = StackSerializer(stack, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ----- DELETE --------------------------------------------------------
    def destroy(self, request, pk=None):
        if not pk:
            return Response(
                {"error": "Stack ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            delete_stack(stack_id=pk)
        except ServiceError as exc:
            return _error_response(exc)

        return Response(
            {"message": "Stack deletion initiated successfully."},
            status=status.HTTP_200_OK,
        )

    # ----- TRIGGER IAC UPDATE -------------------------------------------
    @action(detail=True, methods=["post"], url_path="trigger-iac-update", url_name="trigger_iac_update")
    def trigger_iac_update_action(self, request, pk=None):
        if not pk:
            return Response(
                {"error": "Stack ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            trigger_iac_update(stack_id=pk)
        except ServiceError as exc:
            return _error_response(exc)

        return Response(
            {"message": "Stack update initiated successfully."},
            status=status.HTTP_200_OK,
        )

    # ----- TRAEFIK CONFIG ------------------------------------------------
    @action(detail=False, methods=["get"], url_path="traefik-config", url_name="traefik_config", permission_classes=[AllowAny])
    def get_traefik_config_action(self, request):
        config = get_traefik_config()
        return JsonResponse(config)

    # ----- BULK UPDATE RESOURCES -----------------------------------------
    @action(detail=False, methods=["patch"], url_path="bulk-update-resources", url_name="bulk_update_resources", permission_classes=[AllowAny])
    def bulk_update_resources_action(self, request):
        bulk_update_resources(request.data.get("resources", []))
        return Response(
            {"success": True, "message": "Resources updated successfully."},
            status=status.HTTP_200_OK,
        )

    # ----- DOWNLOAD ------------------------------------------------------
    @action(detail=True, methods=["get"], url_path="download", url_name="download")
    def download(self, request, pk=None):
        if not pk:
            return Response(
                {"error": "Stack ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            file_bytes, file_name = download_stack_source(stack_id=pk)
        except ServiceError as exc:
            return _error_response(exc)

        response = HttpResponse(file_bytes, content_type="application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        return response

    # ----- UPLOAD --------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="upload", url_name="upload")
    def upload(self, request, pk=None):
        if not pk:
            return Response(
                {"error": "Stack ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if "source_zip" not in request.FILES:
            return Response(
                {"error": "No file uploaded. Please include a 'source_zip' field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = upload_source_code(uploaded_file=request.FILES["source_zip"], stack_id=pk)
        except ServiceError as exc:
            return _error_response(exc)

        # Trigger an IAC update now that the upload succeeded
        iac_update_queued = True
        try:
            trigger_iac_update(stack_id=pk)
        except ServiceError:
            iac_update_queued = False  # blob was persisted; deploy can be retried

        return Response(
            {
                "success": True,
                "blob_name": result.blob_name,
                "blob_url": result.blob_url,
                "iac_update_queued": iac_update_queued,
            },
            status=status.HTTP_200_OK,
        )
