import secrets
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .models import ServiceAccountToken

LAST_USED_UPDATE_INTERVAL = timedelta(minutes=1)
INVALID_TOKEN_MESSAGE = 'Invalid service account token.'


class ServiceAccountAuthentication(BaseAuthentication):
    """Authenticate `Authorization: Bearer sa_<id>_<secret>` service tokens.

    Returns (ServiceAccount, ServiceAccountToken). Missing or non-`sa_`
    credentials pass through (return None) so other authenticators are
    unaffected; a present `sa_` credential that fails any check gets a
    generic 401 that never echoes the secret.

    Lookup is by a non-secret token identifier. The presented token digest is
    compared with the stored digest in constant time before acceptance.
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

        identifier = ServiceAccountToken.identifier_from_plaintext(plaintext)
        if identifier is None:
            raise AuthenticationFailed(INVALID_TOKEN_MESSAGE)
        digest = ServiceAccountToken.hash_token(plaintext)

        try:
            token = ServiceAccountToken.objects.select_related(
                'service_account'
            ).get(identifier=identifier)
        except ServiceAccountToken.DoesNotExist:
            raise AuthenticationFailed(INVALID_TOKEN_MESSAGE) from None

        if not secrets.compare_digest(token.digest, digest):
            raise AuthenticationFailed(INVALID_TOKEN_MESSAGE)

        now = timezone.now()
        if not token.is_usable(now) or not token.service_account.is_active:
            raise AuthenticationFailed(INVALID_TOKEN_MESSAGE)

        threshold = now - LAST_USED_UPDATE_INTERVAL
        if (
            token.last_used_at is None
            or token.last_used_at < threshold
        ):
            # Queryset update: at most one write per minute, no updated_at churn
            updated = ServiceAccountToken.objects.filter(
                Q(last_used_at__isnull=True) | Q(last_used_at__lt=threshold),
                pk=token.pk,
            ).update(last_used_at=now)
            if updated:
                token.last_used_at = now

        return (token.service_account, token)

    def authenticate_header(self, request):
        # Without this DRF downgrades 401 responses to 403
        return 'Bearer'
