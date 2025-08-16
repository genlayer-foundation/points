from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ValidatorViewSet

router = DefaultRouter()
router.register(r'', ValidatorViewSet, basename='validator')

urlpatterns = [
    path('', include(router.urls)),
]