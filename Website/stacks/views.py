import random
from inspect import stack
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
import json

try:
    # azure-storage-blob is in requirements.txt; import here so module import error surfaces at runtime
    from azure.storage.blob import BlobServiceClient
except Exception:
    BlobServiceClient = None

from core.decorators import AuthHttpRequest
from stacks.models import Stack, PurchasableStack
from stacks.serializers import (
    StackSerializer,
    PurchasableStackCreateSerializer
)
from projects.models import Project
import stacks.services as services
from django.shortcuts import get_object_or_404
from rest_framework import permissions, filters, viewsets
from stacks.resources.resources_manager import ResourcesManager, create_filtered_data
from stacks.resources.azurerm_resource_group.model import AzurermResourceGroup

class StackViewSet(viewsets.ModelViewSet):
    queryset = Stack.objects.exclude(status="Deleted")
    serializer_class = StackSerializer
    # permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]

    def create(self, request):
        print(request.data)
        project_id = request.data.get('project_id')

        if not project_id:
            return Response(
                {"error": "Project ID is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        purchasable_stack_id = request.data.get('purchasable_stack_id')

        if not purchasable_stack_id:
            return Response(
                {"error": "Purchasable Stack ID is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        purchasable_stack = PurchasableStack.objects.get(pk=purchasable_stack_id)

        list_of_adjectives = [
            "Superb",
            "Incredible",
            "Fantastic",
            "Amazing",
            "Awesome",
            "Brilliant",
            "Exceptional",
            "Outstanding",
            "Remarkable",
            "Extraordinary",
            "Magnificent",
            "Spectacular",
            "Stunning",
            "Impressive",
        ]

        # Generate a random name for the stack
        random_adjective = random.choice(list_of_adjectives)
        stack_name = f'{random_adjective} {purchasable_stack.type} Stack'

        stack = Stack.objects.create(
            name=stack_name,
            project=Project.objects.get(pk=project_id),
            purchased_stack=purchasable_stack
        )

        stack_infrastructure = stack.purchased_stack.stack_infrastructure

        created_resources = ResourcesManager.create(stack_infrastructure, stack)

        data = {
            "stack_id": stack.pk,
            "initial_source_code_zip_blob_name": "mobile.zip",
            # "source_code_location": stack.purchased_stack.source_code_location,
            "resources": ResourcesManager.serialize(created_resources)
        }

        services.send_to_queue('IAC.CREATE', data)

        return Response(data, status=status.HTTP_201_CREATED)
 

    # PATCH: Update a specific stack
    def partial_update(self, request, pk=None):
        """PATCH: Update a specific stack by ID"""
        if not pk:
            return Response(
                {"error": "Stack ID is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        stack = get_object_or_404(Stack, pk=pk)
        serializer = StackSerializer(stack, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Delete
    def destroy(self, request, pk=None):
        """DELETE: Delete a specific stack by ID"""
        if not pk:
            return Response(
                {"error": "Stack ID is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        stack = get_object_or_404(Stack, pk=pk)

        data = {
            "stack_id": stack.pk,
        }

        services.send_to_queue('IAC.DELETE', data)

        return Response({"message": "Stack deletion initiated successfully."}, status=status.HTTP_200_OK)
    

    @action(detail=True, methods=['post'], url_path='trigger-iac-update', url_name='trigger_iac_update')
    def trigger_iac_update(self, request, pk=None):
        if not pk:
            return Response(
                {"error": "Stack ID is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        stack = get_object_or_404(Stack, pk=pk)

        resources = ResourcesManager.get_from_stack(stack)

        data = {
            "stack_id": stack.pk,
            "resources": ResourcesManager.serialize(resources)
        }

        print(json.dumps(data, indent=2))
        services.send_to_queue('IAC.UPDATE', data)

        return Response({"message": "Stack update initiated successfully."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='traefik-config', url_name='traefik_config')
    def get_traefik_config(self, request):
        """GET: Fetch Traefik configuration for all tenant edges."""
        from stacks.resources.deployboxrm_edge.model import DeployBoxrmEdge

        base_domain = getattr(settings, 'BASE_DOMAIN', 'dev.deploy-box.com')
        edges = DeployBoxrmEdge.objects.all()

        routers = {}
        services = {}
        middlewares = {}

        for edge in edges:
            subdomain = edge.subdomain

            # Root route: all non-/api traffic for this tenant
            if edge.resolved_root_base_url:
                routers[f"{subdomain}-root"] = {
                    "rule": f"Host(`{subdomain}.{base_domain}`)",
                    "service": f"{subdomain}-root",
                    "entryPoints": ["web"],
                    "priority": 100,
                }
                services[f"{subdomain}-root"] = {
                    "loadBalancer": {
                        "servers": [{"url": edge.resolved_root_base_url}],
                        "passHostHeader": False,
                    }
                }

            # API route: /api/* traffic for this tenant
            if edge.resolved_api_base_url:
                routers[f"{subdomain}-api"] = {
                    "rule": f"Host(`{subdomain}.{base_domain}`) && PathPrefix(`/api`)",
                    "service": f"{subdomain}-api",
                    "middlewares": [f"{subdomain}-strip-api"],
                    "entryPoints": ["web"],
                    "priority": 200,
                }
                services[f"{subdomain}-api"] = {
                    "loadBalancer": {
                        "servers": [{"url": edge.resolved_api_base_url}],
                        "passHostHeader": False,
                    }
                }
                middlewares[f"{subdomain}-strip-api"] = {
                    "stripPrefix": {"prefixes": ["/api"]}
                }

        return JsonResponse({"http": {"routers": routers, "services": services, "middlewares": middlewares}})

    @action(detail=False, methods=['patch'], url_path='bulk-update-resources', url_name='bulk_update_resources')
    def bulk_update_resources(self, request):
        """PATCH: Bulk update stacks"""

        for resource in request.data.get("resources", []):
            resource_id = resource.get("id")
            resource.pop("stack", None)

            existing_resource = ResourcesManager.read(resource_id)
            if not existing_resource:
                print(f"Resource with ID {resource_id} not found.")
                continue

            if isinstance(existing_resource, list):
                print(f"Resource ID {resource_id} refers to multiple resources; expected a single resource.")
                continue

            existing_resource.__dict__.update(create_filtered_data(resource, type(existing_resource)))
            existing_resource.save()
            print(f"Resource {resource_id} updated successfully.")

        return Response(
            {"success": True, "message": "Resources updated successfully."}, 
            status=status.HTTP_200_OK
        )

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

    @action(detail=True, methods=['get'], url_path='env', url_name='env')
    def get_env(self, request, pk=None):
        """GET: Fetch environment variables for a specific stack"""
        return Response({"error": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=True, methods=['post'], url_path='env', url_name='env')
    def post_env(self, request, pk=None):
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

    @action(detail=True, methods=['delete'], url_path='env', url_name='env')
    def delete_env(self, request, pk=None):
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
