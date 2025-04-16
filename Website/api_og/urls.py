from django.urls import path
from . import views

urlpatterns = [
    # Stack management
    path("", views.stack_handler, name="stack_list"),
    path("create/", views.stack_handler, name="stack_create"),
    path("<str:stack_id>/", views.stack_handler, name="stack_detail"),
    path("<str:stack_id>/update/", views.stack_handler, name="stack_update"),
    path("<str:stack_id>/delete/", views.delete_stack, name="stack_delete"),
    path("<str:stack_id>/download/", views.stack_handler, name="stack_download"),
    path("<str:stack_id>/logs/", views.get_logs, name="stack_logs"),
    # Organization and project specific stack operations
    path(
        "organizations/<str:organization_id>/projects/<str:project_id>/stacks/",
        views.stack_handler,
        name="project_stacks",
    ),
    path(
        "organizations/<str:organization_id>/projects/<str:project_id>/stacks/<str:stack_id>/",
        views.stack_handler,
        name="project_stack_detail",
    ),
    # Usage and billing
    path(
        "usage/database/update/",
        views.update_database_usage,
        name="database_usage_update",
    ),
    path(
        "organizations/<str:organization_id>/projects/<str:project_id>/usage/",
        views.get_usage_per_stack_from_db,
        name="project_usage",
    ),
    path("billing/update/", views.update_cpu_billing, name="billing_update"),
]
