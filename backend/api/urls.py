from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.views import UserViewSet
from contributions.views import ContributionTypeViewSet, ContributionViewSet, EvidenceViewSet, SubmittedContributionViewSet, StewardSubmissionViewSet, HighlightViewSet
from leaderboard.views import GlobalLeaderboardMultiplierViewSet, LeaderboardViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from .metrics_views import ActiveValidatorsView, ContributionTypesStatsView

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'contribution-types', ContributionTypeViewSet)
router.register(r'contributions', ContributionViewSet)
router.register(r'evidence', EvidenceViewSet)
router.register(r'multipliers', GlobalLeaderboardMultiplierViewSet)
router.register(r'leaderboard', LeaderboardViewSet)
router.register(r'submissions', SubmittedContributionViewSet, basename='submission')
router.register(r'steward-submissions', StewardSubmissionViewSet, basename='steward-submission')
router.register(r'highlights', HighlightViewSet, basename='highlight')

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
    
    # Profile endpoints for each category
    path('validators/', include('validators.urls')),
    path('builders/', include('builders.urls')),
    path('stewards/', include('stewards.urls')),
    
    # Authentication endpoints
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Metrics endpoints
    path('metrics/active-validators/', ActiveValidatorsView.as_view(), name='active-validators'),
    path('metrics/contribution-types/', ContributionTypesStatsView.as_view(), name='contribution-types-stats'),
]