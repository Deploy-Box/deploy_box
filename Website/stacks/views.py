import json
from django.http import JsonResponse, HttpRequest, HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet, ModelViewSet
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
import uuid
import datetime

try:
    # azure-storage-blob is in requirements.txt; import here so module import error surfaces at runtime
    from azure.storage.blob import BlobServiceClient
except Exception:
    BlobServiceClient = None

from core.decorators import oauth_required, AuthHttpRequest
from stacks.models import Stack, PurchasableStack
from stacks.serializers import (
    StackSerializer,
    PurchasableStackCreateSerializer
)
from projects.models import Project
import stacks.services as services
from django.shortcuts import get_object_or_404
from rest_framework import permissions, filters
from rest_framework import viewsets

class StackViewSet(viewsets.ModelViewSet):
    queryset = Stack.objects.exclude(status="DELETED")
    serializer_class = StackSerializer
    # permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]

    def create(self, request):
        project_id = request.data.get('project_id')
        purchasable_stack_id = request.data.get('purchasable_stack_id')
        
        if not project_id or not purchasable_stack_id:
            return Response(
                {"error": "project_id and purchasable_stack_id are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        services.add_stack(
            project_id=project_id,
            purchasable_stack_id=purchasable_stack_id,
        )
        return Response({"message": "Stack creation initiated"}, status=status.HTTP_201_CREATED)
    
    
    # Delete
    def destroy(self, request, pk=None):
        """DELETE: Delete a specific stack"""
        stack = get_object_or_404(Stack, id=pk)
        delete_success = services.delete_stack(stack=stack)

        if not delete_success:
            return Response(
                {"error": "Failed to delete stack. Check server logs for details."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {"success": True, "message": "Stack deletion initiated successfully."}, 
            status=status.HTTP_200_OK
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

    @action(detail=True, methods=['get'], url_path='download', url_name='download')
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
        
    @action(detail=True, methods=['post'], url_path='upload', url_name='upload')
    def upload(self, request, pk=None):
        """POST: Upload source code for a specific stack"""
        return services.upload_source_code(request, stack_id=pk)

    @action(detail=True, methods=['post'], url_path='set-persistent', url_name='set_persistent')
    def set_persistent(self, request, pk=None):
        """POST: Set a stack as persistent"""
        stack = get_object_or_404(Stack, id=pk)

        if (services.set_is_persistent_stack(stack=stack, is_persistent=True)):
            return Response(
                {"success": True, "message": "Stack set to persistent successfully."}, 
                status=status.HTTP_200_OK
            )

        return Response(
            {"error": "Failed to set stack as persistent. Check server logs for details."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    @action(detail=True, methods=['get'], url_path='set-non-persistent', url_name='set_non_persistent')
    def set_non_persistent(self, request, pk=None):
        """GET: Set a stack as non-persistent"""
        stack = get_object_or_404(Stack, id=pk)

        if (services.set_is_persistent_stack(stack=stack, is_persistent=False)):
            return Response(
                {"success": True, "message": "Stack set to non-persistent successfully."}, 
                status=status.HTTP_200_OK
            )

        return Response(
            {"error": "Failed to set stack as non-persistent. Check server logs for details."},
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
