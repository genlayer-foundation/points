from rest_framework.routers import SimpleRouter

from .views import AIReviewViewSet

router = SimpleRouter()
router.register(r'', AIReviewViewSet, basename='ai-review')

urlpatterns = router.urls
