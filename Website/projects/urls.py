from django.urls import path
from . import views

urlpatterns = [
    path("", views.base_routing, name="project_base"),
    path("<str:project_id>/", views.get_project, name="get_project"),
]
