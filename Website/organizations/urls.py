from django.urls import path
from . import views

urlpatterns = [
    path("", views.bulk_routing, name="organization_base"),
    path("<str:organization_id>/", views.specific_routing, name="get_organization"),
]
