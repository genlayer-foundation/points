"""
Tests for EthereumAuthentication resolving the user from the Django session.

The authenticator used to run User.objects.get(address__iexact=...) on every
DRF request, which PostgreSQL can only answer with a sequential scan because
the only index on users_user.address is case-sensitive. These tests pin the new
behaviour and the query shape.
"""

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from .testing import login_wallet_session


User = get_user_model()

UNREAD_COUNT_URL = '/api/v1/notifications/unread-count/'
MARK_ALL_READ_URL = '/api/v1/notifications/mark-all-read/'
VERIFY_URL = '/api/auth/verify/'
REFRESH_URL = '/api/auth/refresh/'

# Deliberately mixed case: production still holds mixed-case addresses, and a
# case-sensitive wallet-binding comparison would lock every one of them out.
MIXED_CASE_ADDRESS = '0xAbCdEf1234567890AbCdEf1234567890AbCdEf12'


class WalletSessionAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='wallet@example.com',
            password='testpass123',
            address=MIXED_CASE_ADDRESS,
            is_email_verified=True,
        )

    def test_authenticates_real_login_session(self):
        login_wallet_session(self.client, self.user)

        response = self.client.get(UNREAD_COUNT_URL)

        self.assertEqual(response.status_code, 200)

    def test_lowercase_session_address_matches_mixed_case_db_address(self):
        """The login view stores the lowercased SIWE address."""
        login_wallet_session(self.client, self.user, address=MIXED_CASE_ADDRESS.lower())

        response = self.client.get(UNREAD_COUNT_URL)

        self.assertEqual(response.status_code, 200)

    def test_db_cased_session_address_matches(self):
        """signup_email_confirm stores the address in database casing."""
        login_wallet_session(self.client, self.user, address=self.user.address)

        response = self.client.get(UNREAD_COUNT_URL)

        self.assertEqual(response.status_code, 200)

    def test_rejects_session_without_django_auth_id(self):
        """A pre-django_login session carries no _auth_user_id."""
        session = self.client.session
        session['authenticated'] = True
        session['ethereum_address'] = self.user.address
        session.save()

        self.assertEqual(self.client.get(UNREAD_COUNT_URL).status_code, 403)

        verify = self.client.get(VERIFY_URL)
        self.assertEqual(verify.status_code, 200)
        self.assertFalse(verify.data['authenticated'])

    def test_rejects_inactive_user(self):
        login_wallet_session(self.client, self.user)
        User.objects.filter(pk=self.user.pk).update(is_active=False)

        self.assertEqual(self.client.get(UNREAD_COUNT_URL).status_code, 403)

    def test_rejects_after_password_rotation(self):
        login_wallet_session(self.client, self.user)
        self.user.set_password('a-different-password')
        self.user.save(update_fields=['password'])

        self.assertEqual(self.client.get(UNREAD_COUNT_URL).status_code, 403)
        # Django invalidates the session itself once the auth hash goes stale.
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_rejects_deleted_user(self):
        login_wallet_session(self.client, self.user)
        self.user.delete()

        self.assertEqual(self.client.get(UNREAD_COUNT_URL).status_code, 403)

    def test_rejects_when_db_address_changed(self):
        login_wallet_session(self.client, self.user)
        User.objects.filter(pk=self.user.pk).update(
            address='0x000000000000000000000000000000000000dead'
        )

        self.assertEqual(self.client.get(UNREAD_COUNT_URL).status_code, 403)

    def test_rejects_null_user_address(self):
        login_wallet_session(self.client, self.user)
        User.objects.filter(pk=self.user.pk).update(address=None)

        self.assertEqual(self.client.get(UNREAD_COUNT_URL).status_code, 403)

    def test_does_not_authenticate_as_user_that_took_the_old_address(self):
        """
        Regression guard: an address lookup would authenticate the wrong user
        once the original owner's address moved on.
        """
        login_wallet_session(self.client, self.user)
        old_address = self.user.address
        User.objects.filter(pk=self.user.pk).update(
            address='0x000000000000000000000000000000000000beef'
        )
        other = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            address=old_address,
        )

        response = self.client.get('/api/v1/users/me/')

        self.assertEqual(response.status_code, 403)
        self.assertNotEqual(response.data.get('id'), other.id)

    def test_admin_only_session_still_authenticates(self):
        """Staff sessions carry no wallet keys and fall through to DRF's
        SessionAuthentication, exactly as before."""
        staff = User.objects.create_user(
            email='staff@example.com',
            password='testpass123',
            is_staff=True,
        )
        self.client.force_login(staff, backend='django.contrib.auth.backends.ModelBackend')

        self.assertEqual(self.client.get(UNREAD_COUNT_URL).status_code, 200)

    def test_wallet_switch_reauthenticates(self):
        login_wallet_session(self.client, self.user)
        self.assertEqual(self.client.post('/api/auth/logout/').status_code, 200)

        other = User.objects.create_user(
            email='second@example.com',
            password='testpass123',
            address='0x1111111111111111111111111111111111111111',
        )
        login_wallet_session(self.client, other)

        response = self.client.get('/api/v1/users/me/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], other.id)


class WalletSessionCsrfTests(TestCase):
    def setUp(self):
        # DRF sets _dont_enforce_csrf_checks by default, which would make every
        # assertion here vacuous.
        self.client = APIClient(enforce_csrf_checks=True)
        self.user = User.objects.create_user(
            email='csrf@example.com',
            password='testpass123',
            address=MIXED_CASE_ADDRESS,
        )

    def _csrf_token(self):
        self.client.get('/api/csrf/')
        return self.client.cookies['csrftoken'].value

    def test_safe_method_needs_no_token(self):
        login_wallet_session(self.client, self.user)

        self.assertEqual(self.client.get(UNREAD_COUNT_URL).status_code, 200)

    def test_unsafe_method_without_token_rejected(self):
        login_wallet_session(self.client, self.user)

        response = self.client.post(MARK_ALL_READ_URL)

        self.assertEqual(response.status_code, 403)
        self.assertIn('CSRF', str(response.data.get('detail', '')))

    def test_unsafe_method_with_token_accepted(self):
        token = self._csrf_token()
        login_wallet_session(self.client, self.user)

        response = self.client.post(MARK_ALL_READ_URL, HTTP_X_CSRFTOKEN=token)

        self.assertEqual(response.status_code, 200)

    def test_csrf_enforced_before_user_resolution(self):
        """
        A session the authenticator would reject must still fail on CSRF first,
        proving enforcement did not move behind the user lookup.
        """
        session = self.client.session
        session['authenticated'] = True
        session['ethereum_address'] = self.user.address
        session.save()

        response = self.client.post(MARK_ALL_READ_URL)

        self.assertEqual(response.status_code, 403)
        self.assertIn('CSRF', str(response.data.get('detail', '')))

    def test_login_views_remain_csrf_exempt(self):
        for url in (
            '/api/auth/login/',
            '/api/auth/signup/email/start/',
            '/api/auth/signup/email/resend/',
            '/api/auth/signup/email/confirm/',
        ):
            with self.subTest(url=url):
                response = self.client.post(url, {}, format='json')
                self.assertNotIn(
                    'CSRF', str(getattr(response, 'data', {}) or {}), msg=url
                )


class WalletSessionQueryShapeTests(TestCase):
    """
    Guards the query shape that caused the outage.

    Note on portability: `iexact` compiles to UPPER(...) on PostgreSQL but to
    LIKE ... ESCAPE on SQLite, so asserting on 'upper(' alone would be
    vacuously true on the SQLite-based CI. CaptureQueriesContext records SQL
    with parameters already interpolated, so the address literal itself is
    present under both compilations and is the portable signal.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='shape@example.com',
            password='testpass123',
            address=MIXED_CASE_ADDRESS,
        )

    def test_authenticated_request_does_not_scan_by_address(self):
        # unread-count itself never looks a user up by address, so any address
        # literal in the captured SQL comes from the authenticator.
        login_wallet_session(self.client, self.user)

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(UNREAD_COUNT_URL)

        self.assertEqual(response.status_code, 200)
        sqls = [query['sql'] for query in ctx.captured_queries]
        user_sqls = [sql for sql in sqls if 'users_user' in sql]
        self.assertEqual(len(user_sqls), 1, user_sqls)
        self.assertRegex(user_sqls[0], r'users_user.*\.\W?id\W?\s*=')

        joined = '\n'.join(sqls).lower()
        self.assertNotIn(self.user.address.lower(), joined)
        self.assertNotIn('upper(', joined)

    def test_address_lookup_would_be_detected(self):
        """Keeps the guard above honest on whichever backend is running."""
        with CaptureQueriesContext(connection) as ctx:
            User.objects.filter(address__iexact=self.user.address).first()

        joined = '\n'.join(q['sql'] for q in ctx.captured_queries).lower()
        self.assertIn(self.user.address.lower(), joined)

    def test_verify_auth_costs_one_user_query(self):
        login_wallet_session(self.client, self.user)

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(VERIFY_URL)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['authenticated'])
        user_sqls = [
            query['sql'] for query in ctx.captured_queries
            if 'users_user' in query['sql']
        ]
        self.assertEqual(len(user_sqls), 1, user_sqls)


class VerifyAndRefreshContractTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='contract@example.com',
            password='testpass123',
            address=MIXED_CASE_ADDRESS,
        )

    def test_verify_returns_session_address_verbatim(self):
        login_wallet_session(self.client, self.user, address=self.user.address)

        response = self.client.get(VERIFY_URL)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['authenticated'])
        self.assertEqual(response.data['address'], self.user.address)
        self.assertEqual(response.data['user_id'], self.user.id)
        self.assertNotIn('session_key', response.data)

    def test_verify_reports_false_without_django_auth_id(self):
        session = self.client.session
        session['authenticated'] = True
        session['ethereum_address'] = self.user.address
        session.save()

        response = self.client.get(VERIFY_URL)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['authenticated'])
        self.assertIsNone(response.data['address'])
        self.assertIsNone(response.data['user_id'])
        self.assertFalse(response.data['pending_signup'])

    def test_verify_reports_false_for_admin_only_session(self):
        staff = User.objects.create_user(
            email='adminonly@example.com',
            password='testpass123',
            is_staff=True,
        )
        self.client.force_login(staff, backend='django.contrib.auth.backends.ModelBackend')

        response = self.client.get(VERIFY_URL)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['authenticated'])

    def test_refresh_succeeds_for_real_session(self):
        login_wallet_session(self.client, self.user)

        response = self.client.post(REFRESH_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Session refreshed successfully.')

    def test_pending_signup_does_not_report_the_previous_account(self):
        """
        Starting a signup with an unregistered wallet sets authenticated=False
        but leaves the previous Django login and address in the session, so the
        wallet-session flag has to stay part of the gate. Otherwise DRF's
        SessionAuthentication resolves the old user and verify reports them as
        signed in, hiding the pending-signup branch from the client.
        """
        login_wallet_session(self.client, self.user, address=self.user.address)

        session = self.client.session
        session['authenticated'] = False
        session['pending_wallet_address'] = '0x' + 'a' * 40
        session.save()

        response = self.client.get(VERIFY_URL)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['authenticated'])
        self.assertIsNone(response.data['user_id'])

    def test_pending_signup_session_is_not_refreshed(self):
        login_wallet_session(self.client, self.user, address=self.user.address)

        session = self.client.session
        session['authenticated'] = False
        session.save()

        response = self.client.post(REFRESH_URL)

        self.assertEqual(response.status_code, 401)

    def test_refresh_rejects_session_without_django_auth_id(self):
        session = self.client.session
        session['authenticated'] = True
        session['ethereum_address'] = self.user.address
        session.save()

        response = self.client.post(REFRESH_URL)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data['error'], 'Not authenticated.')
