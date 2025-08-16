from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StewardViewSet

router = DefaultRouter()
router.register(r'', StewardViewSet, basename='steward')

urlpatterns = [
    path('', include(router.urls)),
]