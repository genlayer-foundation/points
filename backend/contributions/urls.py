from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ContributionTypeViewSet, ContributionViewSet, EvidenceViewSet,
    SubmittedContributionViewSet,
    MissionViewSet, StartupRequestViewSet
)

app_name = 'contributions'

# API router
router = DefaultRouter()
router.register(r'types', ContributionTypeViewSet)
router.register(r'contributions', ContributionViewSet)
router.register(r'evidence', EvidenceViewSet)
router.register(r'submissions', SubmittedContributionViewSet, basename='submission')
router.register(r'missions', MissionViewSet, basename='mission')
router.register(r'startup-requests', StartupRequestViewSet, basename='startup-request')

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),
]