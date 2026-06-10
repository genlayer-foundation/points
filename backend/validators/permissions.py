import hmac

from rest_framework.permissions import BasePermission
from django.conf import settings


class IsCronToken(BasePermission):
    """
    Permission class to validate cron job requests.
    Checks for X-Cron-Token header matching CRON_SYNC_TOKEN setting.
    """

    def has_permission(self, request, view):
        token = request.headers.get('X-Cron-Token')
        expected_token = getattr(settings, 'CRON_SYNC_TOKEN', '')
        # Constant-time comparison so the token can't be recovered via timing
        return bool(
            token and expected_token
            and hmac.compare_digest(str(token), str(expected_token))
        )
