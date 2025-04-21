from django.urls import path
from . import views

urlpatterns = [
    path("", views.base_routing, name="project_base"),
    path("<str:project_id>/", views.specific_routing, name="specific_routing"),
]
