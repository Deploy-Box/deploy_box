from django.urls import path
from . import views

app_name = "developer"

urlpatterns = [
    path("", views.developer_home, name="home"),
    path("<str:username>/", views.developer_detail, name="detail"),
    path("<str:username>/showcase/", views.developer_showcase, name="showcase"),
]
