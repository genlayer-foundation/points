from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ContributionTypeViewSet, ContributionViewSet, EvidenceViewSet,
    SubmittedContributionViewSet, SubmissionListView, submission_review_view,
    HighlightViewSet
)

app_name = 'contributions'

# API router
router = DefaultRouter()
router.register(r'types', ContributionTypeViewSet)
router.register(r'contributions', ContributionViewSet)
router.register(r'evidence', EvidenceViewSet)
router.register(r'submissions', SubmittedContributionViewSet, basename='submission')
router.register(r'highlights', HighlightViewSet, basename='highlight')

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),
    
    # Staff management URLs
    path('staff/submissions/', SubmissionListView.as_view(), name='submission-list'),
    path('staff/submissions/<uuid:pk>/edit/', submission_review_view, name='submission-review'),
]