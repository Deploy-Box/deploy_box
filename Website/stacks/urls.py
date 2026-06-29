from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

# Create routers for ViewSets
router = DefaultRouter()
router.register(r'', views.StackViewSet, basename='stack')

urlpatterns = [
    path('admin/check-credit-limits/', views.check_credit_limits_view, name='check-credit-limits'),

    # Deployment log endpoints (IaC webhook-authenticated)
    path('<str:stack_id>/deployment-logs/', views.create_deployment_log_view, name='deployment-log-create'),
    path('<str:stack_id>/deployment-logs/<str:log_id>/append/', views.append_deployment_log_view, name='deployment-log-append'),
    path('<str:stack_id>/deployment-logs/<str:log_id>/complete/', views.complete_deployment_log_view, name='deployment-log-complete'),

    # Deployment log endpoints (user-authenticated)
    path('<str:stack_id>/deployment-logs/latest/', views.latest_deployment_log_view, name='deployment-log-latest'),
    path('<str:stack_id>/deployment-logs/<str:log_id>/', views.deployment_log_detail_view, name='deployment-log-detail'),

    # Operation endpoints (user-authenticated)
    path('<str:stack_id>/operations/', views.stack_operations_view, name='stack-operations'),
    path('operations/<str:operation_id>/', views.operation_detail_view, name='operation-detail'),

    # Operation endpoints (IaC webhook-authenticated)
    path('operations/<str:operation_id>/claim/', views.operation_claim_view, name='operation-claim'),
    path('operations/<str:operation_id>/complete/', views.operation_complete_view, name='operation-complete'),

    # Unified Resource endpoints (Phase 1)
    path('<str:stack_id>/resources-v2/', views.resource_tree_view, name='resource-tree'),
    path('dashboard/<str:project_id>/', views.dashboard_view, name='stack-dashboard'),
] + router.urls
