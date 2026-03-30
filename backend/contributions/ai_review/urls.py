from rest_framework.routers import DefaultRouter

from .views import AIReviewViewSet

router = DefaultRouter()
router.register(r'', AIReviewViewSet, basename='ai-review')

urlpatterns = router.urls
