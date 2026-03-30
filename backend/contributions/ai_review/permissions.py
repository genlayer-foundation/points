from django.conf import settings
from rest_framework.permissions import BasePermission


class IsAIReviewToken(BasePermission):
    """Authenticate requests using the X-AI-Review-Key header."""

    def has_permission(self, request, view):
        token = request.headers.get('X-AI-Review-Key', '')
        expected = getattr(settings, 'AI_REVIEW_API_KEY', '')
        return bool(token and expected and token == expected)
