"""Test helpers for authenticating as a service account."""

from .models import ServiceAccount, ServiceAccountToken


def service_account_auth_headers(scopes, name='test-service-account'):
    """Create a service account + token and return client auth kwargs."""
    account, _ = ServiceAccount.objects.get_or_create(name=name)
    _, plaintext = ServiceAccountToken.issue(account, list(scopes))
    return {'HTTP_AUTHORIZATION': f'Bearer {plaintext}'}
