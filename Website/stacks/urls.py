from rest_framework.routers import DefaultRouter
from . import views

# Create routers for ViewSets
router = DefaultRouter()
router.register(r'', views.StackViewSet, basename='stack')
urlpatterns = router.urls
