from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.views import UserViewSet
from contributions.views import ContributionTypeViewSet, ContributionViewSet
from leaderboard.views import ContributionTypeMultiplierViewSet, LeaderboardViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'contribution-types', ContributionTypeViewSet)
router.register(r'contributions', ContributionViewSet)
router.register(r'multipliers', ContributionTypeMultiplierViewSet)
router.register(r'leaderboard', LeaderboardViewSet)

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
    
    # Authentication endpoints
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]