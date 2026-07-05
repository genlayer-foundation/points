"""
Tests for the service account token system.

Everything here is self-contained: the authentication and scope machinery is
exercised against an in-module test view, with no dependency on any consumer
app or URL. Consumer wiring (the AI review API) is tested in
contributions/tests/test_ai_review_auth.py.
"""

import hashlib
from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
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
        self.assertTrue(plaintext.startswith(f'sa_{token.identifier}_'))
        self.assertEqual(
            token.digest, hashlib.sha256(plaintext.encode()).hexdigest(),
        )
        self.assertNotEqual(token.digest, plaintext)
        self.assertEqual(
            ServiceAccountToken.identifier_from_plaintext(plaintext),
            token.identifier,
        )
        # The plaintext appears in no stored field
        token.refresh_from_db()
        for field in ('identifier', 'digest', 'scopes'):
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

    def test_tampered_secret_with_known_identifier_rejected(self):
        _, token, _ = _issue()
        self.assertEqual(
            _get(f'Bearer sa_{token.identifier}_wrongsecret').status_code,
            401,
        )

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


class IssueServiceAccountTokenCommandTests(TestCase):
    """Management command validation and output contract."""

    def test_rejects_non_positive_expires_days(self):
        with self.assertRaisesMessage(
            CommandError, '--expires-days must be a positive integer.',
        ):
            call_command(
                'issue_service_account_token',
                'agent',
                scopes=['testing:read'],
                expires_days=0,
            )

        self.assertFalse(ServiceAccount.objects.exists())
        self.assertFalse(ServiceAccountToken.objects.exists())

    def test_positive_expires_days_sets_expiry(self):
        output = StringIO()
        before = timezone.now()

        call_command(
            'issue_service_account_token',
            'agent',
            scopes=['testing:read'],
            expires_days=1,
            stdout=output,
        )

        token = ServiceAccountToken.objects.get()
        self.assertGreater(token.expires_at, before)
        self.assertIn(f'Token id: {token.identifier}', output.getvalue())


class ServiceAccountAdminTokenIssueTests(TestCase):
    """Admin token issuance keeps generated secrets out of editable fields."""

    def setUp(self):
        admin_user = get_user_model().objects.create_superuser(
            email='admin@test.com',
            password='password',
        )
        self.client.force_login(admin_user)
        self.account = ServiceAccount.objects.create(name='admin-agent')
        self.issue_url = reverse(
            'admin:service_accounts_serviceaccount_issue_token',
            args=[self.account.pk],
        )

    def test_admin_can_issue_token_for_service_account(self):
        expires_at = timezone.now() + timedelta(days=2)

        response = self.client.post(
            self.issue_url,
            data={
                'scopes': 'testing:read, testing:write testing:read',
                'expires_at_0': expires_at.strftime('%Y-%m-%d'),
                'expires_at_1': expires_at.strftime('%H:%M:%S'),
            },
        )

        self.assertEqual(response.status_code, 200)
        token = ServiceAccountToken.objects.get(service_account=self.account)
        plaintext = response.context['plaintext']
        self.assertTrue(plaintext.startswith(f'sa_{token.identifier}_'))
        self.assertContains(response, plaintext)
        self.assertEqual(token.scopes, ['testing:read', 'testing:write'])
        self.assertNotIn(plaintext, token.digest)
        self.assertGreater(token.expires_at, timezone.now())

    def test_admin_rejects_empty_scopes(self):
        response = self.client.post(
            self.issue_url,
            data={
                'scopes': ' , ',
                'expires_at_0': '',
                'expires_at_1': '',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter at least one scope.')
        self.assertFalse(ServiceAccountToken.objects.exists())
