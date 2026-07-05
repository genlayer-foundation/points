"""
Tests for the service account token system.

Everything here is self-contained: the authentication and scope machinery is
exercised against an in-module test view, with no dependency on any consumer
app or URL. Consumer wiring (the AI review API) is tested in
contributions/tests/test_ai_review_auth.py.
"""

import hashlib
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from service_accounts.authentication import ServiceAccountAuthentication
from service_accounts.models import ServiceAccount, ServiceAccountToken
from service_accounts.permissions import HasServiceAccountScope


class ProtectedView(APIView):
    authentication_classes = [ServiceAccountAuthentication]
    permission_classes = [HasServiceAccountScope]
    required_scopes = {'*': 'testing:read'}

    def get(self, request):
        return Response({'account': request.user.name})


def _issue(scopes=('testing:read',), name='machine'):
    account, _ = ServiceAccount.objects.get_or_create(name=name)
    token, plaintext = ServiceAccountToken.issue(account, list(scopes))
    return account, token, plaintext


def _get(auth_header=None):
    factory = APIRequestFactory()
    kwargs = {'HTTP_AUTHORIZATION': auth_header} if auth_header else {}
    return ProtectedView.as_view()(factory.get('/protected/', **kwargs))


class ServiceAccountTokenModelTests(TestCase):
    """Token issuance, hashing, and parsing."""

    def test_issue_returns_plaintext_once_and_stores_only_digest(self):
        account = ServiceAccount.objects.create(name='agent')
        token, plaintext = ServiceAccountToken.issue(account, ['testing:read'])

        self.assertTrue(plaintext.startswith('sa_'))
        self.assertEqual(
            token.digest, hashlib.sha256(plaintext.encode()).hexdigest(),
        )
        self.assertNotEqual(token.digest, plaintext)
        self.assertEqual(token.identifier, token.digest[:8])
        # The plaintext appears in no stored field
        token.refresh_from_db()
        for field in ('digest', 'scopes'):
            self.assertNotIn(plaintext, str(getattr(token, field)))

    def test_principal_is_not_anonymous_and_not_a_user(self):
        account = ServiceAccount.objects.create(name='agent')
        self.assertTrue(account.is_authenticated)
        self.assertFalse(account.is_anonymous)
        self.assertFalse(hasattr(account, 'set_password'))


class ServiceAccountAuthenticationTests(TestCase):
    """The 401 matrix and scope checks, against an in-module view."""

    def test_missing_header_rejected(self):
        self.assertEqual(_get().status_code, 401)

    def test_non_service_account_bearer_rejected(self):
        self.assertEqual(_get('Bearer garbage').status_code, 401)

    def test_unknown_token_rejected(self):
        self.assertEqual(_get('Bearer sa_nosuchtoken').status_code, 401)

    def test_tampered_token_rejected(self):
        _, _, plaintext = _issue()
        self.assertEqual(_get(f'Bearer {plaintext}x').status_code, 401)

    def test_expired_token_rejected(self):
        account = ServiceAccount.objects.create(name='expired-agent')
        _, plaintext = ServiceAccountToken.issue(
            account, ['testing:read'],
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertEqual(_get(f'Bearer {plaintext}').status_code, 401)

    def test_revoked_token_rejected(self):
        _, token, plaintext = _issue()
        token.revoked_at = timezone.now()
        token.save()
        self.assertEqual(_get(f'Bearer {plaintext}').status_code, 401)

    def test_inactive_service_account_rejected(self):
        account, _, plaintext = _issue()
        account.is_active = False
        account.save()
        self.assertEqual(_get(f'Bearer {plaintext}').status_code, 401)

    def test_valid_token_with_scope_accepted(self):
        account, _, plaintext = _issue()
        response = _get(f'Bearer {plaintext}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['account'], account.name)

    def test_valid_token_without_scope_gets_403(self):
        _, _, plaintext = _issue(scopes=('other:read',))
        self.assertEqual(_get(f'Bearer {plaintext}').status_code, 403)

    def test_last_used_at_updates_are_throttled(self):
        _, token, plaintext = _issue()
        self.assertIsNone(token.last_used_at)

        self.assertEqual(_get(f'Bearer {plaintext}').status_code, 200)
        token.refresh_from_db()
        first_used = token.last_used_at
        first_updated = token.updated_at
        self.assertIsNotNone(first_used)

        # An immediate second request must not write again
        self.assertEqual(_get(f'Bearer {plaintext}').status_code, 200)
        token.refresh_from_db()
        self.assertEqual(token.last_used_at, first_used)
        self.assertEqual(token.updated_at, first_updated)
