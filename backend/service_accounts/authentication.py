from datetime import timedelta

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .models import ServiceAccountToken

LAST_USED_UPDATE_INTERVAL = timedelta(minutes=1)


class ServiceAccountAuthentication(BaseAuthentication):
    """Authenticate `Authorization: Bearer sa_<secret>` service tokens.

    Returns (ServiceAccount, ServiceAccountToken). Missing or non-`sa_`
    credentials pass through (return None) so other authenticators are
    unaffected; a present `sa_` credential that fails any check gets a
    generic 401 that never echoes the secret.

    Lookup is by the unique SHA-256 digest of the presented token, so the
    digest comparison happens inside the indexed query itself.
    """

    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if len(header) != 2 or header[0].lower() != b'bearer':
            return None
        try:
            plaintext = header[1].decode('utf-8')
        except UnicodeDecodeError:
            return None
        if not plaintext.startswith('sa_'):
            return None

        try:
            token = ServiceAccountToken.objects.select_related(
                'service_account'
            ).get(digest=ServiceAccountToken.hash_token(plaintext))
        except ServiceAccountToken.DoesNotExist:
            raise AuthenticationFailed('Invalid service account token.')

        now = timezone.now()
        if not token.is_usable(now) or not token.service_account.is_active:
            raise AuthenticationFailed('Invalid service account token.')

        if (
            token.last_used_at is None
            or now - token.last_used_at > LAST_USED_UPDATE_INTERVAL
        ):
            # Queryset update: at most one write per minute, no updated_at churn
            ServiceAccountToken.objects.filter(pk=token.pk).update(last_used_at=now)
            token.last_used_at = now

        return (token.service_account, token)

    def authenticate_header(self, request):
        # Without this DRF downgrades 401 responses to 403
        return 'Bearer'
