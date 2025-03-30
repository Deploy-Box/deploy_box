from django.urls import path
from . import views

urlpatterns = [
    path("", views.testing, name="testing"),
    path("stacks", views.stack_operations, name="add_stacks"),
    path("stacks/<int:stack_id>/deploy", views.stack_operations, name="deploy_stacks"),
    path("stacks/<int:stack_id>", views.stack_operations, name="get_update_stack"),
    path("stacks/get_all_stacks", views.get_all_stacks, name="get_all_stacks"),
    path("stacks/update_database_usage", views.update_database_usage, name="update_database_usage"),
    path(
        "stacks/<int:stack_id>/download", views.stack_operations, name="download_stack"
    ),
]
