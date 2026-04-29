import json
from django.http import JsonResponse, HttpResponse
from rest_framework import status, filters, viewsets
from rest_framework.decorators import action, api_view, permission_classes as perm_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from core.utils.webhook_auth import verify_iac_webhook_signature
from organizations.models import OrganizationMember
from stacks.models import Stack, PurchasableStack, Operation
from stacks.serializers import (
    StackSerializer,
    StackUserSerializer,
    AddResourceSerializer,
    RemoveResourceSerializer,
    ResourceTypeSerializer,
    DeploymentLogCreateSerializer,
    DeploymentLogAppendSerializer,
    DeploymentLogCompleteSerializer,
    OperationSerializer,
    OperationClaimSerializer,
    OperationCompleteSerializer,
)
from stacks import services as _svc
from stacks.services import (
    ServiceError,
    ValidationError,
    NotFoundError,
    ForbiddenError,
    verify_project_access,
    create_stack,
    create_custom_stack,
    delete_stack,
    trigger_iac_update,
    pause_stack,
    resume_stack,
    check_and_auto_pause_stacks,
    bulk_update_resources,
    add_resource_to_stack,
    remove_resource_from_stack,
    list_stack_resources,
    list_available_resource_types,
    get_traefik_config,
    download_stack_source,
    upload_source_code,
    create_deployment_log,
    append_deployment_log,
    complete_deployment_log,
    get_latest_deployment_log,
    get_deployment_log_content,
    claim_operation,
    complete_operation,
    get_stack_operations,
)


def _error_response(exc: ServiceError) -> Response:
    """Convert a service-layer exception into a DRF Response."""
    return Response({"error": str(exc)}, status=exc.status_code)


def _get_user_org_ids(user):
    """Return the organization IDs the user belongs to."""
    return OrganizationMember.objects.filter(
        user=user
    ).values_list("organization_id", flat=True)


def _verify_stack_access(user, stack_id):
    """Raise NotFoundError if the user has no access to this stack.

    Returns the Stack instance on success so callers can use it directly.
    """
    try:
        stack = Stack.objects.select_related("project__organization").get(
            pk=stack_id
        )
    except Stack.DoesNotExist:
        raise NotFoundError("Stack not found.")

    if stack.status == "Deleted":
        raise NotFoundError("Stack not found.")

    org_id = stack.project.organization_id
    if not OrganizationMember.objects.filter(
        user=user, organization_id=org_id
    ).exists():
        raise NotFoundError("Stack not found.")

    return stack


@api_view(["POST"])
@perm_classes([IsAuthenticated])
def check_credit_limits_view(request):
    """Admin endpoint called by the crontainer to auto-pause over-limit stacks."""
    result = check_and_auto_pause_stacks()
    return Response(result, status=status.HTTP_200_OK)


class StackViewSet(viewsets.ModelViewSet):
    queryset = Stack.objects.exclude(status="Deleted")
    serializer_class = StackSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]

    # Actions that the IAC container-app calls back into, authenticated via
    # HMAC-SHA256 shared secret (see SEC-2).
    WEBHOOK_ACTIONS = ("bulk_update_resources_action", "update_status_action", "update_iac_action")

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

    def get_serializer_class(self):
        if getattr(self, 'action', None) in self.WEBHOOK_ACTIONS:
            return StackSerializer
        return StackUserSerializer

    def get_queryset(self):
        if getattr(self, 'action', None) in self.WEBHOOK_ACTIONS:
            return Stack.objects.exclude(status="Deleted")
        user = self.request.user
        user_org_ids = _get_user_org_ids(user)
        return Stack.objects.filter(
            project__organization_id__in=user_org_ids,
        ).exclude(status="Deleted")

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
                user=request.user,
            )
        except ServiceError as exc:
            return _error_response(exc)

        return Response(data, status=status.HTTP_201_CREATED)

    # ----- CREATE CUSTOM STACK -------------------------------------------
    @action(detail=False, methods=["post"], url_path="custom", url_name="create_custom")
    def create_custom_action(self, request):
        try:
            data = create_custom_stack(
                project_id=request.data.get("project_id"),
                user=request.user,
            )
        except ServiceError as exc:
            return _error_response(exc)

        return Response(data, status=status.HTTP_201_CREATED)

    # ----- ADD RESOURCE --------------------------------------------------
    @action(detail=True, methods=["post"], url_path="add-resource", url_name="add_resource")
    def add_resource_action(self, request, pk=None):
        stack = self.get_object()
        serializer = AddResourceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            resource_data = add_resource_to_stack(
                stack_id=str(stack.pk),
                resource_type=serializer.validated_data["resource_type"],
                config=serializer.validated_data.get("config"),
            )
        except ServiceError as exc:
            return _error_response(exc)

        if serializer.validated_data.get("auto_deploy"):
            try:
                trigger_iac_update(stack_id=str(stack.pk))
            except ServiceError:
                pass  # resource was created; deploy can be retried

        return Response(resource_data, status=status.HTTP_201_CREATED)

    # ----- REMOVE RESOURCE -----------------------------------------------
    @action(detail=True, methods=["post"], url_path="remove-resource", url_name="remove_resource")
    def remove_resource_action(self, request, pk=None):
        stack = self.get_object()
        serializer = RemoveResourceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            remove_resource_from_stack(
                stack_id=str(stack.pk),
                resource_id=serializer.validated_data["resource_id"],
            )
        except ServiceError as exc:
            return _error_response(exc)

        if serializer.validated_data.get("auto_deploy"):
            try:
                trigger_iac_update(stack_id=str(stack.pk))
            except ServiceError:
                pass

        return Response(
            {"message": "Resource removed successfully."},
            status=status.HTTP_200_OK,
        )

    # ----- LIST STACK RESOURCES ------------------------------------------
    @action(detail=True, methods=["get"], url_path="resources", url_name="list_resources")
    def list_resources_action(self, request, pk=None):
        stack = self.get_object()
        try:
            resources = list_stack_resources(stack_id=str(stack.pk))
        except ServiceError as exc:
            return _error_response(exc)

        return Response(resources, status=status.HTTP_200_OK)

    # ----- AVAILABLE RESOURCE TYPES --------------------------------------
    @action(detail=False, methods=["get"], url_path="available-resource-types", url_name="available_resource_types")
    def available_resource_types_action(self, request):
        resource_types = list_available_resource_types()
        serializer = ResourceTypeSerializer(resource_types, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ----- PARTIAL UPDATE ------------------------------------------------
    def partial_update(self, request, pk=None):
        stack = self.get_object()
        serializer = self.get_serializer_class()(stack, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ----- DELETE --------------------------------------------------------
    def destroy(self, request, pk=None):
        stack = self.get_object()
        try:
            delete_stack(stack_id=str(stack.pk))
        except ServiceError as exc:
            return _error_response(exc)

        return Response(
            {"message": "Stack deletion initiated successfully."},
            status=status.HTTP_200_OK,
        )

    # ----- TRIGGER IAC UPDATE -------------------------------------------
    @action(detail=True, methods=["post"], url_path="trigger-iac-update", url_name="trigger_iac_update")
    def trigger_iac_update_action(self, request, pk=None):
        stack = self.get_object()
        try:
            trigger_iac_update(stack_id=str(stack.pk))
        except ServiceError as exc:
            return _error_response(exc)

        return Response(
            {"message": "Stack update initiated successfully."},
            status=status.HTTP_200_OK,
        )

    # ----- PAUSE ---------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="pause", url_name="pause")
    def pause_action(self, request, pk=None):
        stack = self.get_object()
        try:
            pause_stack(stack_id=str(stack.pk))
        except ServiceError as exc:
            return _error_response(exc)

        return Response(
            {"message": "Stack pause initiated successfully."},
            status=status.HTTP_200_OK,
        )

    # ----- RESUME --------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="resume", url_name="resume")
    def resume_action(self, request, pk=None):
        stack = self.get_object()
        try:
            resume_stack(stack_id=str(stack.pk))
        except ServiceError as exc:
            return _error_response(exc)

        return Response(
            {"message": "Stack resume initiated successfully."},
            status=status.HTTP_200_OK,
        )

    # ----- TRAEFIK CONFIG ------------------------------------------------
    @action(detail=False, methods=["get"], url_path="traefik-config", url_name="traefik_config", permission_classes=[AllowAny])
    def get_traefik_config_action(self, request):
        config = get_traefik_config()
        return JsonResponse(config)

    # ----- BULK UPDATE RESOURCES (webhook) --------------------------------
    @action(detail=False, methods=["patch"], url_path="bulk-update-resources", url_name="bulk_update_resources", permission_classes=[AllowAny])
    def bulk_update_resources_action(self, request):
        bulk_update_resources(request.data.get("resources", []))
        return Response(
            {"success": True, "message": "Resources updated successfully."},
            status=status.HTTP_200_OK,
        )

    # ----- UPDATE RESOURCES (user-facing) --------------------------------
    @action(detail=True, methods=["patch"], url_path="update-resources", url_name="update_resources")
    def update_resources_action(self, request, pk=None):
        stack = self.get_object()
        resources_data = request.data.get("resources", [])
        if not resources_data:
            return Response(
                {"error": "No resources provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate that all resource IDs belong to this stack
        from stacks.resources.resources_manager import ResourcesManager
        stack_resources = ResourcesManager.get_from_stack(stack)
        stack_resource_ids = {str(r.id) for r in stack_resources}
        for resource in resources_data:
            rid = resource.get("id")
            if rid and rid not in stack_resource_ids:
                return Response(
                    {"error": f"Resource {rid} does not belong to this stack."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        bulk_update_resources(resources_data)
        return Response(
            {"success": True, "message": "Resources updated successfully."},
            status=status.HTTP_200_OK,
        )

    # ----- DOWNLOAD ------------------------------------------------------
    @action(detail=True, methods=["get"], url_path="download", url_name="download")
    def download(self, request, pk=None):
        stack = self.get_object()
        try:
            file_bytes, file_name = download_stack_source(stack_id=str(stack.pk))
        except ServiceError as exc:
            return _error_response(exc)

        response = HttpResponse(file_bytes, content_type="application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        return response

    # ----- UPLOAD --------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="upload", url_name="upload")
    def upload(self, request, pk=None):
        stack = self.get_object()

        if "source_zip" not in request.FILES:
            return Response(
                {"error": "No file uploaded. Please include a 'source_zip' field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = upload_source_code(uploaded_file=request.FILES["source_zip"], stack_id=str(stack.pk))
        except ServiceError as exc:
            return _error_response(exc)

        # Trigger an IAC update now that the upload succeeded
        iac_update_queued = True
        try:
            trigger_iac_update(stack_id=str(stack.pk))
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

    # ----- UPDATE STATUS -------------------------------------------------
    @action(detail=True, methods=["post"], url_path="update_status", url_name="update_status")
    def update_status_action(self, request, pk=None):
        if "status" not in request.data:
            return Response(
                {"status": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_status = request.data.get("status")
        if not new_status:
            return Response(
                {"error": "Status is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            stack = Stack.objects.get(pk=pk)
        except Stack.DoesNotExist:
            return Response(
                {"error": "Stack not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        old_status = stack.status
        result = _svc.update_stack_status(str(stack.pk), new_status)
        if not result:
            return Response(
                {"success": False, "error": "Failed to update stack status"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            "success": True,
            "message": "Stack status updated successfully",
            "stack_id": str(stack.pk),
            "old_status": old_status,
            "new_status": new_status,
        })

    # ----- UPDATE IAC (database only, no deployment) --------------------
    @action(detail=True, methods=["post"], url_path="update_iac", url_name="update_iac")
    def update_iac_action(self, request, pk=None):
        if "data" not in request.data:
            return Response(
                {"data": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_iac = request.data.get("data")
        if not new_iac:
            return Response(
                {"error": "IAC configuration is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(new_iac, dict):
            return Response(
                {"error": "IAC configuration must be a valid JSON object"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            stack = Stack.objects.get(pk=pk)
        except Stack.DoesNotExist:
            return Response(
                {"error": "Stack not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        old_iac = dict(stack.iac_state)
        result = _svc.update_stack_iac_only(str(stack.pk), new_iac)
        if not result:
            return Response(
                {"error": "Failed to update IAC configuration"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            "success": True,
            "message": "IAC configuration updated successfully (no deployment)",
            "stack_id": str(stack.pk),
            "old_iac": old_iac,
            "new_iac": new_iac,
        })


# ---------------------------------------------------------------------------
# Standalone overwrite-IAC view (uses stack_id kwarg, not pk)
# ---------------------------------------------------------------------------
# Deployment Log views (standalone functions, not ViewSet actions)
# ---------------------------------------------------------------------------
def _verify_webhook_and_parse(request, serializer_class=None):
    """Helper: verify HMAC webhook signature, optionally validate body."""
    verify_iac_webhook_signature(request)
    if serializer_class:
        serializer = serializer_class(data=request.data)
        if not serializer.is_valid():
            return None, Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return serializer.validated_data, None
    return request.data, None


@api_view(["POST"])
@perm_classes([AllowAny])
def create_deployment_log_view(request, stack_id):
    """IaC creates a new deployment log for a stack (webhook auth)."""
    data, err = _verify_webhook_and_parse(request, DeploymentLogCreateSerializer)
    if err:
        return err

    try:
        result = create_deployment_log(stack_id, data["operation"])
    except ServiceError as exc:
        return _error_response(exc)

    return Response(result, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@perm_classes([AllowAny])
def append_deployment_log_view(request, stack_id, log_id):
    """IaC appends log text to an existing deployment log (webhook auth)."""
    data, err = _verify_webhook_and_parse(request, DeploymentLogAppendSerializer)
    if err:
        return err

    success = append_deployment_log(log_id, data["text"])
    if not success:
        return Response(
            {"error": "Log not found or not running"},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response({"success": True})


@api_view(["POST"])
@perm_classes([AllowAny])
def complete_deployment_log_view(request, stack_id, log_id):
    """IaC marks a deployment log as completed or failed (webhook auth)."""
    data, err = _verify_webhook_and_parse(request, DeploymentLogCompleteSerializer)
    if err:
        return err

    try:
        success = complete_deployment_log(log_id, data["status"])
    except ServiceError as exc:
        return _error_response(exc)

    if not success:
        return Response(
            {"error": "Log not found or not running"},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response({"success": True})


@api_view(["GET"])
@perm_classes([IsAuthenticated])
def latest_deployment_log_view(request, stack_id):
    """Frontend fetches the most recent deployment log for a stack."""
    try:
        _verify_stack_access(request.user, stack_id)
    except NotFoundError as exc:
        return _error_response(exc)

    result = get_latest_deployment_log(stack_id)
    if not result:
        return Response(
            {"error": "No deployment logs found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(result)


@api_view(["GET"])
@perm_classes([IsAuthenticated])
def deployment_log_detail_view(request, stack_id, log_id):
    """Frontend polls for deployment log content with ?after_line=N."""
    try:
        _verify_stack_access(request.user, stack_id)
    except NotFoundError as exc:
        return _error_response(exc)

    after_line = int(request.query_params.get("after_line", 0))
    if after_line < 0:
        after_line = 0

    result = get_deployment_log_content(log_id, after_line)
    if not result:
        return Response(
            {"error": "Deployment log not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(result)


# ---------------------------------------------------------------------------
# Operation views — lifecycle tracking for IaC jobs
# ---------------------------------------------------------------------------
@api_view(["GET"])
@perm_classes([IsAuthenticated])
def operation_detail_view(request, operation_id):
    """Frontend polls for operation status."""
    try:
        operation = Operation.objects.select_related(
            "stack__project__organization"
        ).get(pk=operation_id)
    except Operation.DoesNotExist:
        return Response({"error": "Operation not found"}, status=status.HTTP_404_NOT_FOUND)

    org_id = operation.stack.project.organization_id
    if not OrganizationMember.objects.filter(
        user=request.user, organization_id=org_id
    ).exists():
        return Response({"error": "Operation not found"}, status=status.HTTP_404_NOT_FOUND)

    return Response(OperationSerializer(operation).data)


@api_view(["GET"])
@perm_classes([IsAuthenticated])
def stack_operations_view(request, stack_id):
    """List recent operations for a stack."""
    try:
        _verify_stack_access(request.user, stack_id)
    except NotFoundError as exc:
        return _error_response(exc)

    try:
        result = get_stack_operations(stack_id)
    except NotFoundError as exc:
        return _error_response(exc)

    return Response(result)


@api_view(["POST"])
@perm_classes([AllowAny])
def operation_claim_view(request, operation_id):
    """IaC job claims an operation for processing (HMAC-authenticated)."""
    data, error_resp = _verify_webhook_and_parse(request, OperationClaimSerializer)
    if error_resp:
        return error_resp

    try:
        result = claim_operation(
            operation_id=operation_id,
            attempt_id=data["attempt_id"],
            lease_duration_seconds=data.get("lease_duration_seconds", 1800),
        )
    except (NotFoundError, ValidationError) as exc:
        return _error_response(exc)

    return Response(result)


@api_view(["POST"])
@perm_classes([AllowAny])
def operation_complete_view(request, operation_id):
    """IaC job marks an operation as succeeded or failed (HMAC-authenticated)."""
    data, error_resp = _verify_webhook_and_parse(request, OperationCompleteSerializer)
    if error_resp:
        return error_resp

    try:
        result = complete_operation(
            operation_id=operation_id,
            attempt_id=data["attempt_id"],
            status=data["status"],
            error_message=data.get("error_message", ""),
        )
    except (NotFoundError, ValidationError) as exc:
        return _error_response(exc)

    return Response(result)
