from django.urls import path
from . import views

urlpatterns = [
    path("", views.base_routing, name="stack_base"),
    path("purchasable/", views.purchasable_stack_routing, name="purchasable_stack"),
]
