from django.http import JsonResponse, HttpRequest, HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.decorators import oauth_required, AuthHttpRequest
import stacks.handlers as handlers
from stacks.models import Stack, PurchasableStack
from stacks.serializers import (
    StackDatabaseSerializer,
    StackSerializer,
    StackCreateSerializer,
    StackUpdateSerializer,
    PurchasableStackCreateSerializer,
    StackDatabaseUpdateSerializer,
    StackIACOverwriteSerializer,
    StackStatusUpdateSerializer,
    StackIACUpdateSerializer,
    StackIACStateUpdateSerializer,
)
from projects.models import Project
import stacks.services as services
from django.shortcuts import get_object_or_404

class StackViewSet(ViewSet):
    """
    ViewSet for managing stacks
    """

    @oauth_required()
    def list(self, request):
        """GET: Fetch available stacks"""
        stack_id = request.query_params.get("stack_id")
        if not stack_id:
            return Response({"error": "Stack ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Get the stack directly from the database
        try:
            stack = get_object_or_404(Stack, id=stack_id)
            serializer = StackSerializer(stack)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @oauth_required()
    def create(self, request):
        """POST: Add a new stack"""
        serializer = StackCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Verify that project and purchasable stack exist
        try:
            project = get_object_or_404(Project, id=data['project_id'])
            purchasable_stack = get_object_or_404(PurchasableStack, id=data['purchasable_stack_id'])
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        stack = services.add_stack(
            project_id=data['project_id'],
            purchasable_stack_id=data['purchasable_stack_id'],
            name=data['name'],
        )

        return Response({"success": True, "stack_id": stack.id}, status=status.HTTP_201_CREATED)

    @oauth_required()
    def retrieve(self, request, pk=None):
        """GET: Fetch a specific stack"""
        stack_id = pk
        if not stack_id:
            return Response({"error": "Stack ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Get the stack directly from the database
        try:
            stack = get_object_or_404(Stack, id=stack_id)
            serializer = StackSerializer(stack)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @oauth_required()
    def update(self, request, pk=None):
        """PUT: Update a specific stack"""
        stack = get_object_or_404(Stack, id=pk)
        serializer = StackUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        root_directory = data.get('root_directory')

        success = services.update_stack(stack, root_directory)
        return Response({"success": success})

    @oauth_required()
    def partial_update(self, request, pk=None):
        """PATCH: Partially update a specific stack"""
        stack = get_object_or_404(Stack, id=pk)
        serializer = StackUpdateSerializer(data=request.data, partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        root_directory = data.get('root_directory')

        success = services.update_stack(stack, root_directory)
        return Response({"success": success})

    @oauth_required()
    def destroy(self, request, pk=None):
        """DELETE: Delete a specific stack"""
        stack = get_object_or_404(Stack, id=pk)
        print(f"Deleting stack: {stack.id}")
        stack_deleted = services.delete_stack(stack)

        if not stack_deleted:
            return Response({"error": "Failed to delete stack."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {"success": True, "message": "Stack deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

    @oauth_required()
    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        """POST: Refresh a specific stack's infrastructure"""
        stack = get_object_or_404(Stack, id=pk)
        
        # Check if stack has IAC configuration
        if not stack.iac:
            return Response(
                {"error": "No infrastructure configuration found for this stack."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        refresh_success = services.refresh_stack(stack)

        if not refresh_success:
            return Response(
                {"error": "Failed to refresh stack infrastructure. Check server logs for details."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {"success": True, "message": "Stack infrastructure refreshed successfully."}, 
            status=status.HTTP_200_OK
        )

    @oauth_required()
    @action(detail=True, methods=['post'])
    def overwrite_iac(self, request, pk=None):
        """POST: Overwrite IAC configuration for a specific stack"""
        stack = get_object_or_404(Stack, id=pk)
        serializer = StackIACOverwriteSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        new_iac = data.get('iac')

        if not new_iac:
            return Response({"error": "IAC configuration is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Call the service function and handle the JsonResponse
        result = services.update_iac(str(stack.id), new_iac)
        
        # Convert JsonResponse to DRF Response
        if result.status_code == 200:
            return Response(result.json(), status=status.HTTP_200_OK)
        else:
            return Response(result.json(), status=result.status_code)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """POST: Update the status of a specific stack"""
        stack = get_object_or_404(Stack, id=pk)
        serializer = StackStatusUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        new_status = data.get('status')

        if not new_status:
            return Response({"error": "Status is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Store the old status before updating
        old_status = stack.status
        success = services.update_stack_status(stack, new_status)
        
        if success:
            return Response({
                "success": True, 
                "message": f"Stack status updated successfully to '{new_status}'",
                "stack_id": str(stack.id),
                "old_status": old_status,
                "new_status": new_status
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "success": False,
                "error": "Failed to update stack status"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def update_iac(self, request, pk=None):
        """POST: Update IAC configuration for a specific stack (full overwrite)"""
        stack = get_object_or_404(Stack, id=pk)
        serializer = StackIACUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        new_iac = data.get('data')

        if not new_iac:
            return Response({"error": "IAC configuration is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate that the new IAC is a valid dictionary
        if not isinstance(new_iac, dict):
            return Response({"error": "IAC configuration must be a valid JSON object."}, status=status.HTTP_400_BAD_REQUEST)

        # Store the old IAC before updating
        old_iac = stack.iac
        
        # Update only the IAC field without deployment
        success = services.update_stack_iac_only(stack, new_iac)
        
        if success:
            return Response({
                "success": True,
                "message": "IAC configuration updated successfully (no deployment)",
                "stack_id": str(stack.id),
                "old_iac": old_iac,
                "new_iac": new_iac
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "success": False,
                "error": "Failed to update IAC configuration"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(detail=True, methods=['post'])
    def update_iac_state(self, request, pk=None):
        """POST: Update IAC state for a specific stack"""
        stack = get_object_or_404(Stack, id=pk)
        serializer = StackIACStateUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        new_iac_state = data.get('data')

        if not new_iac_state:
            return Response({"error": "IAC state is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Store the old IAC state before updating
        old_iac_state = stack.iac_state

        # Update only the IAC state field without deployment
        success = services.update_stack_iac_state_only(stack, new_iac_state)

        if success:
            return Response({
                "success": True,
                "message": "IAC state updated successfully (no deployment)",
                "stack_id": str(stack.id),
                "old_iac_state": old_iac_state,
                "new_iac_state": new_iac_state
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "success": False,
                "error": "Failed to update IAC state"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @oauth_required()
    @action(detail=True, methods=['get'])
    def env(self, request, pk=None):
        """GET: Fetch environment variables for a specific stack"""
        return Response({"error": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=True, methods=['post'])
    def env(self, request, pk=None):
        """POST: Update environment variables for a specific stack"""
        from stacks.forms import EnvFileUploadForm

        form = EnvFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            selected_frameworks = form.cleaned_data["framework"]
            selected_locations = form.cleaned_data["select_location"]
            uploaded_file = form.cleaned_data["env_file"]

            return services.post_stack_env(
                pk, selected_frameworks, selected_locations, uploaded_file
            )
        else:
            return Response({"message": "you must upload a valid form"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def env(self, request, pk=None):
        """DELETE: Delete environment variables for a specific stack"""
        return Response({"error": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """GET: Download stack source code"""
        return self._download_stack(request, pk)

    def _download_stack(self, request, stack_id):
        """Helper method for downloading stack source code"""
        import requests
        from django.conf import settings

        # Get the stack object
        try:
            stack = Stack.objects.get(id=stack_id)
        except Stack.DoesNotExist:
            return Response({"error": "Stack not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check if DEPLOY_BOX_STACK_ENDPOINT is configured
        if not hasattr(settings, 'DEPLOY_BOX_STACK_ENDPOINT') or not settings.DEPLOY_BOX_STACK_ENDPOINT:
            return Response(
                {"error": "DEPLOY_BOX_STACK_ENDPOINT is not configured"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            # Construct the download URL using the environment variable
            file_name = f"{stack.purchased_stack.type}-{stack.purchased_stack.variant}.zip".lower()
            download_url = f"{settings.DEPLOY_BOX_STACK_ENDPOINT.rstrip('/')}/{file_name}"
            print(f"Attempting to download from: {download_url}")
            
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()

            # Create the response with file download headers
            file_response = HttpResponse(
                response.content, content_type="application/octet-stream"
            )
            file_response["Content-Disposition"] = (
                f'attachment; filename="{file_name}"'
            )
            return file_response

        except requests.RequestException as e:
            print(f"Failed to download from DEPLOY_BOX_STACK_ENDPOINT: {str(e)}")
            return Response(
                {"error": f"Failed to download file from configured endpoint: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PurchasableStackViewSet(ViewSet):
    """
    ViewSet for managing purchasable stacks
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """GET: Fetch available purchasable stacks"""
        return Response({"error": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)

    def create(self, request):
        """POST: Add a new purchasable stack"""
        serializer = PurchasableStackCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Check if the purchasable stack already exists
        purchasable_stack = PurchasableStack.objects.filter(price_id=data['price_id']).first()

        if purchasable_stack:
            return Response({"error": "Purchasable stack already exists."}, status=status.HTTP_400_BAD_REQUEST)

        return services.post_purchasable_stack(
            data['type'],
            data['variant'],
            data['version'],
            data['price_id']
        )

    def update(self, request, pk=None):
        """PUT: Update a purchasable stack"""
        return Response({"error": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)

    def partial_update(self, request, pk=None):
        """PATCH: Partially update a purchasable stack"""
        return Response({"error": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)

    def destroy(self, request, pk=None):
        """DELETE: Delete a purchasable stack"""
        return Response({"error": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)


class StackDatabaseViewSet(ViewSet):
    """
    ViewSet for managing stack databases
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """GET: Fetch all stack databases"""
        stack_databases = services.get_all_stack_databases()
        serializer = StackDatabaseSerializer(stack_databases, many=True)

        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    @method_decorator(csrf_exempt)
    @action(detail=False, methods=['post'])
    def update_usage(self, request):
        """POST: Update stack databases usage"""
        serializer = StackDatabaseUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data['data']
        success = services.update_stack_databases_usages(data)

        if not success:
            return Response(
                {"error": "Failed to update stack databases usages."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({"success": True}, status=status.HTTP_200_OK)


class LogsAPIView(APIView):
    """
    API View for getting logs
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, service_name):
        """GET: Fetch logs for a specific service"""
        return Response({"message": "not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)


# Legacy function-based views for backward compatibility (can be removed later)
@oauth_required()
def base_routing(request: AuthHttpRequest) -> JsonResponse:
    """Legacy function-based view - use StackViewSet instead"""
    viewset = StackViewSet()
    viewset.request = request

    if request.method == "GET":
        return viewset.list(request)
    elif request.method == "POST":
        return viewset.create(request)
    else:
        return JsonResponse({"error": "Method not allowed."}, status=405)


@oauth_required()
def specific_routing(request: AuthHttpRequest, stack_id: str) -> JsonResponse:
    """Legacy function-based view - use StackViewSet instead"""
    viewset = StackViewSet()
    viewset.request = request

    if request.method == "GET":
        return viewset.retrieve(request, pk=stack_id)
    elif request.method == "POST":
        return viewset.update(request, pk=stack_id)
    elif request.method == "DELETE":
        return viewset.destroy(request, pk=stack_id)
    elif request.method == "PATCH":
        return viewset.partial_update(request, pk=stack_id)
    else:
        return JsonResponse({"error": "Method not allowed."}, status=405)


@oauth_required()
def purchasable_stack_routing(request: AuthHttpRequest) -> JsonResponse:
    """Legacy function-based view - use PurchasableStackViewSet instead"""
    viewset = PurchasableStackViewSet()
    viewset.request = request

    if request.method == "GET":
        return viewset.list(request)
    elif request.method == "POST":
        return viewset.create(request)
    else:
        return JsonResponse({"error": "Method not allowed."}, status=405)


def stack_env_routing(request: AuthHttpRequest, stack_id: str) -> JsonResponse:
    """Legacy function-based view - use StackViewSet env action instead"""
    viewset = StackViewSet()
    viewset.request = request

    if request.method == "GET":
        return viewset.env(request, pk=stack_id)
    elif request.method == "POST":
        return viewset.env(request, pk=stack_id)
    elif request.method == "DELETE":
        return viewset.env(request, pk=stack_id)
    else:
        return JsonResponse({"error": "Method not allowed."}, status=405)


def download_stack(request: HttpRequest, stack_id: str):
    """Legacy function-based view - use StackViewSet download action instead"""
    viewset = StackViewSet()
    viewset.request = request
    return viewset.download(request, pk=stack_id)


def get_all_stack_databases(request: HttpRequest) -> JsonResponse:
    """Legacy function-based view - use StackDatabaseViewSet instead"""
    viewset = StackDatabaseViewSet()
    viewset.request = request
    return viewset.list(request)


@csrf_exempt
def update_stack_databases_usages(request: HttpRequest) -> JsonResponse:
    """Legacy function-based view - use StackDatabaseViewSet update_usage action instead"""
    viewset = StackDatabaseViewSet()
    viewset.request = request
    return viewset.update_usage(request)


def get_logs(request: HttpRequest, service_name: str) -> JsonResponse:
    """Legacy function-based view - use LogsAPIView instead"""
    view = LogsAPIView()
    view.request = request
    return view.get(request, service_name)

def update_iac(request: HttpRequest, stack_id: str) -> JsonResponse:
    """Legacy function-based view - use StackViewSet update action instead"""
    if request.method == "POST":
        return handlers.overwrite_iac(request, stack_id)
    else:
        return JsonResponse({"error": "Method not allowed."}, status=405)


def update_stack_information(request: HttpRequest, stack_id: str) -> JsonResponse:
    """Legacy function-based view - use StackViewSet update_stack_information action instead"""
    if request.method == "POST":
        return handlers.update_stack_information(request, stack_id)
    else:
        return JsonResponse({"error": "Method not allowed."}, status=405)

def overwrite_iac(request: HttpRequest, stack_id: str) -> JsonResponse:
    """Legacy function-based view - use StackViewSet overwrite_iac action instead"""
    if request.method == "POST":
        return handlers.overwrite_iac(request, stack_id)
    else:
        return JsonResponse({"error": "Method not allowed."}, status=405)

def update_iac_state(request: HttpRequest, stack_id: str) -> JsonResponse:
    """Legacy function-based view - use StackViewSet update_iac_state action instead"""
    if request.method == "POST":
        return handlers.update_iac_state(request, stack_id)
    else:
        return JsonResponse({"error": "Method not allowed."}, status=405)