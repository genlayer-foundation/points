from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BuilderViewSet

router = DefaultRouter()
router.register(r'', BuilderViewSet, basename='builder')

urlpatterns = [
    path('', include(router.urls)),
]