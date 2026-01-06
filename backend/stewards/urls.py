from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StewardViewSet, WorkingGroupViewSet

router = DefaultRouter()
# Register working-groups first to ensure it matches before the catch-all steward route
router.register(r'working-groups', WorkingGroupViewSet, basename='working-group')
router.register(r'', StewardViewSet, basename='steward')

urlpatterns = [
    path('', include(router.urls)),
]