from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from eth_account import Account
from eth_account.messages import encode_defunct
from rest_framework.test import APIClient

from campaigns.models import CampaignLink, UserAcquisitionAttribution
from campaigns.services import apply_pending_attribution, record_user_acquisition
from campaigns.tests.test_models import make_campaign, make_link
from ethereum_auth.models import Nonce, PendingWalletSignup

User = get_user_model()


def make_pending(address='0xabcdefabcdefabcdefabcdefabcdefabcdefabcd', **kwargs):
    defaults = {'address': address, 'expires_at': timezone.now() + timedelta(minutes=30)}
    defaults.update(kwargs)
    return PendingWalletSignup.objects.create(**defaults)


def attribution_payload(link, **overrides):
    payload = {
        'utm_id': link.tracking_id,
        'landing_path': '/builders',
        'captured_at': timezone.now().isoformat(),
    }
    payload.update(overrides)
    return payload


class ApplyPendingAttributionTests(TestCase):
    def setUp(self):
        self.link = make_link()
        self.pending = make_pending()

    def test_valid_utm_id_writes_fk_and_snapshot(self):
        apply_pending_attribution(self.pending, attribution_payload(self.link))
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.acquisition_campaign_link, self.link)
        self.assertIsNotNone(self.pending.acquisition_captured_at)
        snapshot = self.pending.acquisition_snapshot
        self.assertEqual(snapshot['link_tracking_id'], self.link.tracking_id)
        self.assertEqual(snapshot['campaign_key'], 'ethcc_role_recruitment')
        self.assertEqual(snapshot['source'], 'x')
        self.assertEqual(snapshot['medium'], 'organic_social')
        self.assertEqual(snapshot['link_role'], 'builder')
        self.assertEqual(snapshot['landing_path'], '/builders')

    def test_snapshot_never_copies_browser_utm_text(self):
        payload = attribution_payload(self.link, utm_source='SPOOFED', campaign='SPOOFED')
        apply_pending_attribution(self.pending, payload)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.acquisition_snapshot['source'], 'x')
        self.assertNotIn('SPOOFED', str(self.pending.acquisition_snapshot))

    def test_unknown_utm_id_is_silently_ignored(self):
        apply_pending_attribution(self.pending, attribution_payload(self.link, utm_id='cl-unknown'))
        self.pending.refresh_from_db()
        self.assertIsNone(self.pending.acquisition_captured_at)

    def test_link_not_live_at_capture_time_ignored(self):
        CampaignLink.objects.filter(pk=self.link.pk).update(is_active=False)
        apply_pending_attribution(self.pending, attribution_payload(self.link))
        self.pending.refresh_from_db()
        self.assertIsNone(self.pending.acquisition_captured_at)

    def test_captured_at_outside_window_ignored(self):
        stale = (timezone.now() - timedelta(days=45)).isoformat()
        apply_pending_attribution(self.pending, attribution_payload(self.link, captured_at=stale))
        future = (timezone.now() + timedelta(days=2)).isoformat()
        apply_pending_attribution(self.pending, attribution_payload(self.link, captured_at=future))
        self.pending.refresh_from_db()
        self.assertIsNone(self.pending.acquisition_captured_at)

    def test_first_touch_never_overwritten(self):
        apply_pending_attribution(self.pending, attribution_payload(self.link))
        other_link = make_link(make_campaign(tracking_key='other_campaign'), alias='other')
        apply_pending_attribution(self.pending, attribution_payload(other_link))
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.acquisition_campaign_link, self.link)

    def test_reset_clears_stale_attribution(self):
        apply_pending_attribution(self.pending, attribution_payload(self.link))
        apply_pending_attribution(self.pending, None, reset=True)
        self.pending.refresh_from_db()
        self.assertIsNone(self.pending.acquisition_campaign_link)
        self.assertEqual(self.pending.acquisition_snapshot, {})
        self.assertIsNone(self.pending.acquisition_captured_at)

    def test_reset_then_new_attribution_applies(self):
        apply_pending_attribution(self.pending, attribution_payload(self.link))
        other_link = make_link(make_campaign(tracking_key='other_campaign'), alias='other')
        apply_pending_attribution(self.pending, attribution_payload(other_link), reset=True)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.acquisition_campaign_link, other_link)

    def test_malformed_payloads_never_raise(self):
        for payload in (
            None,
            [],
            'string',
            {},
            {'utm_id': 42},
            {'utm_id': 'x' * 200},
            {'utm_id': self.link.tracking_id},  # missing captured_at
            {'utm_id': self.link.tracking_id, 'captured_at': 'not-a-date'},
            {'utm_id': self.link.tracking_id, 'captured_at': '2026-01-01T00:00:00'},  # naive
            attribution_payload(self.link, landing_path='https://evil.example.com'),
            attribution_payload(self.link, landing_path='x' * 500),
        ):
            apply_pending_attribution(self.pending, payload)
        self.pending.refresh_from_db()
        # The two payloads with a bad landing_path are otherwise valid: they
        # attribute with an empty landing path rather than failing.
        self.assertEqual(self.pending.acquisition_snapshot.get('landing_path'), '')


class RecordUserAcquisitionTests(TestCase):
    def setUp(self):
        self.link = make_link()
        self.pending = make_pending()
        apply_pending_attribution(self.pending, attribution_payload(self.link))
        self.pending.refresh_from_db()
        self.user = User.objects.create_user(email='acq@example.com', password='x')

    def test_creates_write_once_record_from_snapshot(self):
        record_user_acquisition(self.user, self.pending)
        record = UserAcquisitionAttribution.objects.get(user=self.user)
        self.assertEqual(record.campaign_link, self.link)
        self.assertEqual(record.link_tracking_id, self.link.tracking_id)
        self.assertEqual(record.campaign_key, 'ethcc_role_recruitment')
        self.assertEqual(record.source, 'x')
        self.assertEqual(record.link_role, 'builder')
        self.assertIsNotNone(record.registered_at)

        # Second call is a no-op.
        record_user_acquisition(self.user, self.pending)
        self.assertEqual(UserAcquisitionAttribution.objects.filter(user=self.user).count(), 1)

    def test_no_attribution_no_record(self):
        blank_pending = make_pending(address='0x1111111111111111111111111111111111111111')
        record_user_acquisition(self.user, blank_pending)
        record_user_acquisition(self.user, None)
        self.assertFalse(UserAcquisitionAttribution.objects.exists())

    def test_failure_does_not_poison_outer_transaction(self):
        with transaction.atomic():
            with patch(
                'campaigns.services.UserAcquisitionAttribution.objects.create',
                side_effect=RuntimeError('boom'),
            ):
                record_user_acquisition(self.user, self.pending)
            # The outer transaction must still be usable after the failure.
            marker = User.objects.create_user(email='still-works@example.com', password='x')
        self.assertTrue(User.objects.filter(pk=marker.pk).exists())
        self.assertFalse(UserAcquisitionAttribution.objects.exists())


class LoginAttributionIntegrationTests(TestCase):
    """The SIWE login view resolves browser attribution onto the pending signup."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.link = make_link()

    def _session_key(self):
        session = self.client.session
        session.save()
        return session.session_key

    def _nonce(self, value):
        return Nonce.objects.create(
            value=value,
            session_key=self._session_key(),
            purpose=Nonce.PURPOSE_LOGIN,
            expires_at=timezone.now() + timedelta(minutes=5),
        )

    def _login_message(self, account, nonce_value):
        return (
            'localhost:5173 wants you to sign in with your Ethereum account:\n'
            f'{account.address}\n\n'
            'Sign in with Ethereum to GenLayer Testnet Contributions\n\n'
            'URI: http://localhost:5173\n'
            'Version: 1\n'
            'Chain ID: 1\n'
            f'Nonce: {nonce_value}\n'
            f'Issued At: {timezone.now().isoformat()}'
        )

    def _login(self, account, nonce_value, attribution=None):
        nonce = self._nonce(nonce_value)
        message = self._login_message(account, nonce.value)
        signature = Account.sign_message(
            encode_defunct(text=message), private_key=account.key,
        ).signature.hex()
        payload = {'message': message, 'signature': signature}
        if attribution is not None:
            payload['attribution'] = attribution
        return self.client.post('/api/auth/login/', payload, format='json')

    def test_login_with_attribution_populates_pending(self):
        account = Account.create()
        response = self._login(account, 'attribNonce1', attribution_payload(self.link))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['pending_signup'])
        pending = PendingWalletSignup.objects.get(address=account.address.lower())
        self.assertEqual(pending.acquisition_campaign_link, self.link)

    def test_repeated_login_keeps_first_touch(self):
        account = Account.create()
        self._login(account, 'attribNonce2', attribution_payload(self.link))
        other_link = make_link(make_campaign(tracking_key='other_campaign'), alias='other')
        self._login(account, 'attribNonce3', attribution_payload(other_link))
        pending = PendingWalletSignup.objects.get(address=account.address.lower())
        self.assertEqual(pending.acquisition_campaign_link, self.link)

    def test_expired_pending_reuse_resets_stale_attribution(self):
        account = Account.create()
        self._login(account, 'attribNonce4', attribution_payload(self.link))
        PendingWalletSignup.objects.filter(address=account.address.lower()).update(
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self._login(account, 'attribNonce5')
        pending = PendingWalletSignup.objects.get(address=account.address.lower())
        self.assertIsNone(pending.acquisition_campaign_link)
        self.assertIsNone(pending.acquisition_captured_at)

    def test_garbage_attribution_never_blocks_signup(self):
        account = Account.create()
        response = self._login(
            account, 'attribNonce6', {'utm_id': ['not', 'a', 'string'], 'captured_at': 12345},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['pending_signup'])

    def test_existing_user_login_ignores_attribution(self):
        account = Account.create()
        User.objects.create_user(
            email='existing@example.com', password='x', address=account.address.lower(),
        )
        response = self._login(account, 'attribNonce7', attribution_payload(self.link))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['authenticated'])
        self.assertFalse(response.data['created'])
        self.assertFalse(PendingWalletSignup.objects.filter(address=account.address.lower()).exists())
        self.assertFalse(UserAcquisitionAttribution.objects.exists())


@override_settings(TURNSTILE_SECRET_KEY='test-secret', TURNSTILE_ALLOWED_HOSTNAMES=[])
class EmailConfirmAttributionTests(TestCase):
    """Email confirmation copies the pending attribution into the durable
    acquisition record in the same transaction that creates the user."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.link = make_link()

    def _pending_signup_in_session(self):
        pending = make_pending()
        apply_pending_attribution(pending, attribution_payload(self.link))
        pending.refresh_from_db()
        session = self.client.session
        session['pending_wallet_signup_id'] = pending.id
        session['pending_wallet_address'] = pending.address
        session.save()
        return pending

    def _start_and_confirm(self, email='campaign-user@example.com'):
        with (
            patch('ethereum_auth.email_verification._generate_verification_code', return_value='123456'),
            patch('ethereum_auth.email_verification.validate_email') as mock_validate_email,
            patch('ethereum_auth.email_verification.requests.post') as mock_post,
        ):
            mock_post.return_value = Mock(json=lambda: {'success': True, 'hostname': 'localhost'})
            mock_validate_email.return_value = SimpleNamespace(
                normalized=email, domain=email.split('@', 1)[1],
            )
            start = self.client.post('/api/auth/signup/email/start/', {
                'email': email,
                'name': 'Campaign User',
                'turnstile_token': 'ok-token',
            }, format='json')
            self.assertEqual(start.status_code, 200, start.data)
            # Confirm re-validates the email, so it must run inside the patches.
            return self.client.post('/api/auth/signup/email/confirm/', {'code': '123456'}, format='json')

    def test_confirm_creates_acquisition_record(self):
        pending = self._pending_signup_in_session()
        response = self._start_and_confirm()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['created'])
        user = User.objects.get(address__iexact=pending.address)
        record = UserAcquisitionAttribution.objects.get(user=user)
        self.assertEqual(record.campaign_link, self.link)
        self.assertEqual(record.campaign_key, 'ethcc_role_recruitment')

    def test_confirm_survives_attribution_failure(self):
        pending = self._pending_signup_in_session()
        with patch(
            'campaigns.services.UserAcquisitionAttribution.objects.create',
            side_effect=RuntimeError('boom'),
        ):
            response = self._start_and_confirm(email='resilient@example.com')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['created'])
        self.assertTrue(User.objects.filter(address__iexact=pending.address).exists())
        self.assertFalse(UserAcquisitionAttribution.objects.exists())
