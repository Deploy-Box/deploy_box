from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated

from projects import services
from projects.services import ServiceError


def _error_response(exc: ServiceError) -> Response:
    """Convert a service-layer exception into a DRF Response."""
    return Response({"error": str(exc)}, status=exc.status_code)


class ProjectViewSet(ViewSet):
    """DRF ViewSet for project CRUD — delegates to service layer."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        data = services.get_projects(request.user)
        return Response({"data": data})

    def retrieve(self, request, pk=None):
        project = services.get_project(request.user, pk)
        if project is None:
            return Response({"message": "Project not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(project, status=status.HTTP_200_OK)

    def create(self, request):
        name = request.data.get("name")
        description = request.data.get("description", "")
        organization_id = request.data.get("organization")

        if not name or not organization_id:
            return Response(
                {"error": "name and organization are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = services.create_project(
                user=request.user,
                name=name,
                description=description,
                organization_id=organization_id,
            )
        except ServiceError as exc:
            return _error_response(exc)

        return Response(data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        try:
            data = services.delete_project(project_id=pk, user=request.user)
        except ServiceError as exc:
            return _error_response(exc)

        return Response(data, status=status.HTTP_200_OK)