from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from stacks.models import Stack

# Create routers for ViewSets
router = DefaultRouter()
router.register(r'', views.StackViewSet, basename='stack')
router.register(r'purchasable-stacks', views.PurchasableStackViewSet, basename='purchasable-stack')

urlpatterns = []

# Include router URLs
urlpatterns += router.urls

# Additional URL patterns for specific actions
urlpatterns += [
    # Legacy function-based views (for backward compatibility)
    # path("", views.base_routing, name="stack_base"),
    # path("<str:stack_id>/", views.specific_routing, name="specific_routing"),
    path("<str:stack_id>/env/", views.stack_env_routing, name="stack_env"),
    # path("purchasable/", views.purchasable_stack_routing, name="purchasable_stack"),
    path("<str:stack_id>/download/", views.download_stack, name="download_stack"),
    path("<str:stack_id>/upload/", views.upload_source_code, name="upload_source_code"),
    # path("get-logs/<str:service_name>/", views.get_logs, name="get_logs"),
    # path(
    #     "admin/databases/",
    #     views.get_all_stack_databases,
    #     name="get_all_stack_databases",
    # ),
    # path(
    #     "admin/databases/update_database_usage/",
    #     views.update_stack_databases_usages,
    #     name="update_stack_databases_usages",
    # ),
]

# New DRF class-based view URLs
urlpatterns += [
    # Logs API View
    path("logs/<str:service_name>/", views.LogsAPIView.as_view(), name="logs_api"),
]

urlpatterns += [
    path("<str:stack_id>/update-iac/", views.update_iac, name="update_iac"),
    path("<str:stack_id>/update-stack-information/", views.update_stack_information, name="update_stack_information"),
]

# urlpatterns += Stack.get_urlpatterns(baseurl="")
