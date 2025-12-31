from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from stacks.models import Stack

# Create routers for ViewSets
router = DefaultRouter()
router.register(r'', views.StackViewSet, basename='stack')
router.register(r'purchasable-stacks', views.PurchasableStackViewSet, basename='purchasable-stack')
urlpatterns = router.urls
