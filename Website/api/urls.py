from django.urls import path
from . import views

urlpatterns = [
    path("", views.testing, name="testing"),
    path("stacks/", views.stack_operations, name="add_stacks"),
    path("stacks/<int:stack_id>/", views.stack_operations, name="get_update_stack"),
    path(
        "stacks/<int:stack_id>/download", views.stack_operations, name="download_stack"
    ),
    path(
        "get_available_deployments",
        views.get_available_deployments,
        name="get_available_deployments",
    ),
    path("upload_deployment/", views.upload_deployment, name="upload_deployment"),
    path("patch_deployment/", views.patch_deployment, name="patch_deployment"),
    path(
        "get_deployment_details/<int:deployment_id>/",
        views.get_deployment_details,
        name="get_deployment_details",
    ),
]
