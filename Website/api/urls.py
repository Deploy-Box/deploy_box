from django.urls import path
from . import views

urlpatterns = [
    path("", views.stack_operations, name="add_stacks"),
    path("<str:organization_id>/<str:project_id>/<str:stack_id>/", views.stack_operations, name="get_update_stack"),
    path("<str:organization_id>/<str:project_id>/<str:stack_id>/deploy", views.stack_operations, name="deploy_stacks"),
    path("<str:organization_id>/<str:project_id>/get_all_stacks", views.get_all_stacks, name="get_all_stacks"),
    path("<str:organization_id>/<str:project_id>/update_database_usage", views.update_database_usage, name="update_database_usage"),
    path("<str:organization_id>/<str:project_id>/get_stack_usage_from_db", views.get_usage_per_stack_from_db, name="get_usage_per_stack_from_db"),
    path("<str:organization_id>/<str:project_id>/<str:stack_id>/download", views.stack_operations, name="download_stack"),
    
    path("update-billing/", views.update_cpu_billing, name="update_cpu_billing")
]
