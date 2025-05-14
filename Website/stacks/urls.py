from django.urls import path
from . import views

urlpatterns = [
    path("", views.base_routing, name="stack_base"),
    path("<str:stack_id>/", views.specific_routing, name="specific_routing"),
    path("<str:stack_id>/env/", views.stack_env_routing, name="stack_env"),
    path("purchasable/", views.purchasable_stack_routing, name="purchasable_stack"),
    path("<str:stack_id>/download/", views.download_stack, name="download_stack"),
]
