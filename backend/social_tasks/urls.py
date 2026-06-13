from rest_framework.routers import DefaultRouter

from .views import SocialTaskViewSet

router = DefaultRouter()
router.register(r'social-tasks', SocialTaskViewSet, basename='social-task')

urlpatterns = router.urls
