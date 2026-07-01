from types import SimpleNamespace
from unittest.mock import Mock, patch

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from eth_account import Account
from eth_account.messages import encode_defunct
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .email_verification import email_fingerprint, encrypt_email, token_lookup_hash
from .models import EmailVerificationToken, Nonce, PendingWalletSignup


User = get_user_model()


class EthereumAuthResponseSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='wallet@example.com',
            password='testpass123',
            address='0x1234567890abcdef1234567890abcdef12345678',
            is_email_verified=True,
        )

    def test_verify_auth_does_not_return_session_key(self):
        session = self.client.session
        session['authenticated'] = True
        session['ethereum_address'] = self.user.address
        session.save()

        response = self.client.get('/api/auth/verify/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['authenticated'])
        self.assertEqual(response.data['address'], self.user.address)
        self.assertNotIn('session_key', response.data)

    def test_unauthenticated_verify_auth_does_not_return_session_key(self):
        response = self.client.get('/api/auth/verify/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['authenticated'])
        self.assertNotIn('session_key', response.data)


@override_settings(
    ETHEREUM_AUTH={
        'SIWE_DOMAIN': 'localhost',
        'NONCE_EXPIRY_MINUTES': 5,
    },
    FRONTEND_URL='http://localhost:5173',
)
class EthereumAuthNoncePurposeTests(TestCase):
    def setUp(self):
        self.client = APIClient()

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

    def _recovery_message(self, account, nonce_value):
        return (
            'localhost:5173 wants you to verify a wallet for GenLayer POAP recovery:\n'
            f'{account.address}\n\n'
            'This signature only proves ownership of this wallet for attaching legacy POAPs '
            'to your current portal account. It will not sign you into the portal or change your account.\n\n'
            f'Portal Account: {account.address}\n'
            'URI: http://localhost:5173\n'
            'Version: 1\n'
            'Chain ID: 1\n'
            f'Nonce: {nonce_value}\n'
            f'Issued At: {timezone.now().isoformat()}'
        )

    def _sign(self, account, message):
        return Account.sign_message(
            encode_defunct(text=message),
            private_key=account.key,
        ).signature.hex()

    def test_nonce_endpoint_defaults_to_login_purpose(self):
        response = self.client.get('/api/auth/nonce/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['purpose'], Nonce.PURPOSE_LOGIN)
        self.assertTrue(
            Nonce.objects.filter(
                value=response.data['nonce'],
                purpose=Nonce.PURPOSE_LOGIN,
            ).exists()
        )

    def test_nonce_endpoint_accepts_poap_recovery_purpose(self):
        response = self.client.get('/api/auth/nonce/?purpose=poap_recovery')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['purpose'], Nonce.PURPOSE_POAP_RECOVERY)
        self.assertTrue(
            Nonce.objects.filter(
                value=response.data['nonce'],
                purpose=Nonce.PURPOSE_POAP_RECOVERY,
            ).exists()
        )

    def test_login_accepts_frontend_host_when_siwe_domain_omits_port(self):
        account = Account.create()
        nonce = Nonce.objects.create(
            value='localLoginNonce1',
            purpose=Nonce.PURPOSE_LOGIN,
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
        )
        message = self._login_message(account, nonce.value)

        response = self.client.post('/api/auth/login/', {
            'message': message,
            'signature': self._sign(account, message),
        }, format='json')

        self.assertEqual(response.status_code, 200)
        nonce.refresh_from_db()
        self.assertTrue(nonce.used)
        self.assertFalse(response.data['authenticated'])
        self.assertTrue(response.data['pending_signup'])
        self.assertFalse(User.objects.filter(address__iexact=account.address).exists())

    def test_login_ignores_oversized_referral_code_for_pending_signup(self):
        account = Account.create()
        nonce = Nonce.objects.create(
            value='oversizedReferralNonce1',
            purpose=Nonce.PURPOSE_LOGIN,
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
        )
        message = self._login_message(account, nonce.value)

        response = self.client.post('/api/auth/login/', {
            'message': message,
            'signature': self._sign(account, message),
            'referral_code': 'ABCDEFGHIJK',
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['pending_signup'])
        pending = PendingWalletSignup.objects.get(address=account.address.lower())
        self.assertEqual(pending.referral_code, '')

    def test_known_wallet_logs_in_normally(self):
        account = Account.create()
        user = User.objects.create_user(
            email='known@example.com',
            password='testpass123',
            address=account.address.lower(),
            is_email_verified=True,
        )
        nonce = Nonce.objects.create(
            value='knownWalletNonce1',
            purpose=Nonce.PURPOSE_LOGIN,
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
        )
        message = self._login_message(account, nonce.value)

        response = self.client.post('/api/auth/login/', {
            'message': message,
            'signature': self._sign(account, message),
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['authenticated'])
        self.assertEqual(response.data['user_id'], user.id)
        self.assertEqual(response.data['referral_code'], user.referral_code)
        self.assertFalse(response.data.get('pending_signup', False))

    def test_known_wallet_login_survives_referral_code_generation_failure(self):
        account = Account.create()
        user = User.objects.create_user(
            email='known-no-referral@example.com',
            password='testpass123',
            address=account.address.lower(),
            is_email_verified=True,
        )
        User.objects.filter(pk=user.pk).update(referral_code='')
        user.refresh_from_db()
        nonce = Nonce.objects.create(
            value='knownWalletNoReferral1',
            purpose=Nonce.PURPOSE_LOGIN,
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
        )
        message = self._login_message(account, nonce.value)

        with patch.object(User, 'ensure_referral_code', side_effect=Exception('referral unavailable')):
            response = self.client.post('/api/auth/login/', {
                'message': message,
                'signature': self._sign(account, message),
            }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['authenticated'])
        self.assertEqual(response.data['user_id'], user.id)
        self.assertEqual(response.data['referral_code'], '')

    def test_login_rejects_recovery_purpose_nonce(self):
        account = Account.create()
        nonce = Nonce.objects.create(
            value='recoveryNonceForLogin1',
            purpose=Nonce.PURPOSE_POAP_RECOVERY,
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
        )
        message = self._login_message(account, nonce.value)

        response = self.client.post('/api/auth/login/', {
            'message': message,
            'signature': self._sign(account, message),
        }, format='json')

        self.assertEqual(response.status_code, 400)
        nonce.refresh_from_db()
        self.assertFalse(nonce.used)

    def test_login_rejects_recovery_message_shape(self):
        account = Account.create()
        nonce = Nonce.objects.create(
            value='recoveryMessageNonce1',
            purpose=Nonce.PURPOSE_POAP_RECOVERY,
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
        )
        message = self._recovery_message(account, nonce.value)

        response = self.client.post('/api/auth/login/', {
            'message': message,
            'signature': self._sign(account, message),
        }, format='json')

        self.assertEqual(response.status_code, 400)
        nonce.refresh_from_db()
        self.assertFalse(nonce.used)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_VERIFICATION_ENCRYPTION_KEY=Fernet.generate_key().decode(),
    TURNSTILE_SECRET_KEY='test-secret',
    TURNSTILE_ALLOWED_HOSTNAMES=[],
    EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS=0,
)
class EmailVerificationPipelineTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _valid_email_result(self, email):
        return SimpleNamespace(normalized=email, domain=email.split('@', 1)[1])

    def _pending_signup(self, address='0xabcdefabcdefabcdefabcdefabcdefabcdefabcd'):
        pending = PendingWalletSignup.objects.create(
            address=address,
            expires_at=timezone.now() + timezone.timedelta(minutes=30),
        )
        session = self.client.session
        session['pending_wallet_signup_id'] = pending.id
        session['pending_wallet_address'] = pending.address
        session.save()
        return pending

    def _authenticate(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def _start_pending_email(
        self,
        pending,
        *,
        email='new@example.com',
        code='123456',
        name='New User',
    ) -> EmailVerificationToken:
        with (
            patch('ethereum_auth.email_verification._generate_verification_code', return_value=code),
            patch('ethereum_auth.email_verification.validate_email') as mock_validate_email,
            patch('ethereum_auth.email_verification.requests.post') as mock_post,
        ):
            mock_post.return_value = Mock(json=lambda: {'success': True, 'hostname': 'localhost'})
            mock_validate_email.return_value = self._valid_email_result(email)
            response = self.client.post('/api/auth/signup/email/start/', {
                'email': email,
                'name': name,
                'turnstile_token': 'ok-token',
            }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(address__iexact=pending.address).exists())
        return EmailVerificationToken.objects.get(pending_signup=pending)

    @patch('ethereum_auth.email_verification.requests.post')
    def test_email_start_sends_no_mail_when_turnstile_fails(self, mock_post):
        self._pending_signup()
        mock_post.return_value = Mock(json=lambda: {'success': False})

        response = self.client.post('/api/auth/signup/email/start/', {
            'email': 'new@example.com',
            'turnstile_token': 'bad-token',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(EmailVerificationToken.objects.count(), 0)

    @patch(
        'ethereum_auth.email_verification._generate_verification_code',
        new=Mock(return_value='123456'),
    )
    @patch('ethereum_auth.email_verification.validate_email')
    @patch('ethereum_auth.email_verification.requests.post')
    def test_pending_signup_email_confirm_creates_user_after_valid_token(
        self,
        mock_post,
        mock_validate_email,
    ):
        pending = self._pending_signup()
        mock_post.return_value = Mock(json=lambda: {'success': True, 'hostname': 'localhost'})
        mock_validate_email.return_value = self._valid_email_result('new@example.com')

        response = self.client.post('/api/auth/signup/email/start/', {
            'email': 'new@example.com',
            'name': 'New User',
            'selected_role': 'builder',
            'turnstile_token': 'ok-token',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('123456', mail.outbox[0].body)
        self.assertNotIn('/verify-email?token=', mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].alternatives[0][1], 'text/html')
        self.assertIn('One-time code', mail.outbox[0].alternatives[0][0])
        self.assertIn('123456', mail.outbox[0].alternatives[0][0])
        self.assertIn('GenLayer Portal', mail.outbox[0].alternatives[0][0])
        self.assertFalse(User.objects.filter(address__iexact=pending.address).exists())

        response = self.client.post('/api/auth/signup/email/confirm/', {
            'code': '123456',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['selected_role'], 'builder')
        user = User.objects.get(address__iexact=pending.address)
        self.assertEqual(user.email, 'new@example.com')
        self.assertEqual(user.name, 'New User')
        self.assertTrue(user.is_email_verified)
        self.assertIsNotNone(user.email_verified_at)
        self.assertEqual(response.data['referral_code'], user.referral_code)

    @patch(
        'ethereum_auth.email_verification._generate_verification_code',
        new=Mock(return_value='234567'),
    )
    @patch('ethereum_auth.email_verification.validate_email')
    @patch('ethereum_auth.email_verification.requests.post')
    def test_pending_signup_email_confirm_requires_same_pending_session(
        self,
        mock_post,
        mock_validate_email,
    ):
        pending = self._pending_signup()
        mock_post.return_value = Mock(json=lambda: {'success': True, 'hostname': 'localhost'})
        mock_validate_email.return_value = self._valid_email_result('new-session@example.com')

        response = self.client.post('/api/auth/signup/email/start/', {
            'email': 'new-session@example.com',
            'name': 'New Session User',
            'selected_role': 'validator',
            'turnstile_token': 'ok-token',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        other_client = APIClient()
        response = other_client.post('/api/auth/signup/email/confirm/', {
            'code': '234567',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'Pending signup is required.')
        self.assertFalse(User.objects.filter(address__iexact=pending.address).exists())

        response = self.client.post('/api/auth/signup/email/confirm/', {
            'code': '234567',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['authenticated'])
        self.assertFalse(response.data['requires_wallet_login'])
        self.assertEqual(response.data['selected_role'], 'validator')
        user = User.objects.get(address__iexact=pending.address)
        self.assertEqual(user.email, 'new-session@example.com')
        self.assertEqual(response.data['referral_code'], user.referral_code)

    def test_pending_signup_email_confirm_survives_referral_code_generation_failure(self):
        pending = self._pending_signup(address='0x2222222222222222222222222222222222222222')
        self._start_pending_email(
            pending,
            email='no-referral@example.com',
            code='654321',
            name='No Referral User',
        )

        with (
            patch('ethereum_auth.email_verification.validate_email') as mock_validate_email,
            patch.object(User, 'ensure_referral_code', side_effect=Exception('referral unavailable')),
        ):
            mock_validate_email.return_value = self._valid_email_result('no-referral@example.com')
            response = self.client.post('/api/auth/signup/email/confirm/', {
                'code': '654321',
            }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['authenticated'])
        self.assertEqual(response.data['referral_code'], '')

    def test_pending_signup_wrong_token_fails_without_creating_user(self):
        pending = self._pending_signup()
        token = self._start_pending_email(pending, code='345678')

        response = self.client.post('/api/auth/signup/email/confirm/', {
            'code': '111111',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(address__iexact=pending.address).exists())
        token.refresh_from_db()
        self.assertEqual(token.attempts, 1)
        self.assertIsNone(token.consumed_at)

    def test_pending_signup_expired_token_fails_without_creating_user(self):
        pending = self._pending_signup()
        token = self._start_pending_email(pending, code='456789')
        token.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        token.save(update_fields=['expires_at'])

        response = self.client.post('/api/auth/signup/email/confirm/', {
            'code': '456789',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(address__iexact=pending.address).exists())

    def test_pending_signup_over_attempt_limit_fails_without_creating_user(self):
        pending = self._pending_signup()
        token = self._start_pending_email(pending, code='567890')
        token.attempts = settings.EMAIL_VERIFICATION_MAX_ATTEMPTS
        token.save(update_fields=['attempts'])

        response = self.client.post('/api/auth/signup/email/confirm/', {
            'code': '567890',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(address__iexact=pending.address).exists())

    @override_settings(EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS=60)
    @patch('ethereum_auth.email_verification.requests.post')
    def test_pending_signup_cooldown_blocks_before_turnstile(self, mock_post):
        pending = self._pending_signup()
        pending.last_email_sent_at = timezone.now()
        pending.save(update_fields=['last_email_sent_at'])

        response = self.client.post('/api/auth/signup/email/start/', {
            'email': 'new@example.com',
            'turnstile_token': 'ok-token',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(int(response.data['cooldown_seconds']), 60)
        mock_post.assert_not_called()
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(EmailVerificationToken.objects.count(), 0)

    @override_settings(EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS=60)
    @patch('ethereum_auth.email_verification.requests.post')
    def test_existing_user_cooldown_blocks_before_turnstile(self, mock_post):
        user = User.objects.create_user(
            email='old-cooldown@example.com',
            password='testpass123',
            address='0x4444444444444444444444444444444444444444',
            is_email_verified=False,
        )
        self._authenticate(user)
        EmailVerificationToken.objects.create(
            purpose=EmailVerificationToken.PURPOSE_EXISTING_USER,
            user=user,
            encrypted_email=encrypt_email('changed-cooldown@example.com'),
            email_fingerprint=email_fingerprint('changed-cooldown@example.com'),
            token_lookup_hash=token_lookup_hash('123456'),
            token_hash=make_password('123456'),
            last_sent_at=timezone.now(),
            expires_at=timezone.now() + timezone.timedelta(minutes=30),
        )

        response = self.client.post('/api/auth/email/start/', {
            'email': 'changed-cooldown@example.com',
            'turnstile_token': 'ok-token',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(int(response.data['cooldown_seconds']), 60)
        mock_post.assert_not_called()
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(EmailVerificationToken.objects.count(), 1)

    @patch(
        'ethereum_auth.email_verification._generate_verification_code',
        new=Mock(return_value='678901'),
    )
    @patch(
        'ethereum_auth.email_verification.EmailMultiAlternatives.send',
        new=Mock(side_effect=Exception('SMTP down')),
    )
    @patch('ethereum_auth.email_verification.validate_email')
    @patch('ethereum_auth.email_verification.requests.post')
    def test_pending_signup_mail_send_failure_rolls_back_token_and_cooldown(
        self,
        mock_post,
        mock_validate_email,
    ):
        pending = self._pending_signup()
        mock_post.return_value = Mock(json=lambda: {'success': True, 'hostname': 'localhost'})
        mock_validate_email.return_value = self._valid_email_result('new@example.com')

        response = self.client.post('/api/auth/signup/email/start/', {
            'email': 'new@example.com',
            'turnstile_token': 'ok-token',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(EmailVerificationToken.objects.count(), 0)
        pending.refresh_from_db()
        self.assertIsNone(pending.last_email_sent_at)

    @patch('ethereum_auth.email_verification.validate_email')
    @patch('ethereum_auth.email_verification.requests.post')
    def test_duplicate_user_email_is_rejected_before_mail_send(self, mock_post, mock_validate_email):
        self._pending_signup()
        User.objects.create_user(
            email='taken@example.com',
            password='testpass123',
            address='0x9999999999999999999999999999999999999999',
            is_email_verified=True,
        )
        mock_post.return_value = Mock(json=lambda: {'success': True, 'hostname': 'localhost'})
        mock_validate_email.return_value = self._valid_email_result('taken@example.com')

        response = self.client.post('/api/auth/signup/email/start/', {
            'email': 'taken@example.com',
            'turnstile_token': 'ok-token',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(EmailVerificationToken.objects.count(), 0)

    @patch(
        'ethereum_auth.email_verification._generate_verification_code',
        new=Mock(return_value='789012'),
    )
    @patch('ethereum_auth.email_verification.validate_email')
    @patch('ethereum_auth.email_verification.requests.post')
    def test_existing_user_email_confirm_updates_email(
        self,
        mock_post,
        mock_validate_email,
    ):
        user = User.objects.create_user(
            email='old@example.com',
            password='testpass123',
            address='0x1234567890abcdef1234567890abcdef12345678',
            is_email_verified=False,
        )
        self._authenticate(user)
        mock_post.return_value = Mock(json=lambda: {'success': True, 'hostname': 'localhost'})
        mock_validate_email.return_value = self._valid_email_result('changed@example.com')

        response = self.client.post('/api/auth/email/start/', {
            'email': 'changed@example.com',
            'turnstile_token': 'ok-token',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('789012', mail.outbox[0].body)
        self.assertNotIn('/verify-email?token=', mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].alternatives[0][1], 'text/html')
        user.refresh_from_db()
        self.assertEqual(user.email, 'old@example.com')
        self.assertFalse(user.is_email_verified)

        response = self.client.post('/api/auth/email/confirm/', {
            'code': '789012',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.email, 'changed@example.com')
        self.assertTrue(user.is_email_verified)
        self.assertIsNotNone(user.email_verified_at)

    @patch('ethereum_auth.email_verification.validate_email')
    def test_existing_user_email_confirm_accepts_legacy_token_payload(
        self,
        mock_validate_email,
    ):
        user = User.objects.create_user(
            email='old-token@example.com',
            password='testpass123',
            address='0x3333333333333333333333333333333333333333',
            is_email_verified=False,
        )
        self._authenticate(user)
        legacy_token = 'legacy-token-with-url-safe-length-1234567890'
        email = 'changed-token@example.com'
        mock_validate_email.return_value = self._valid_email_result(email)
        EmailVerificationToken.objects.create(
            purpose=EmailVerificationToken.PURPOSE_EXISTING_USER,
            user=user,
            encrypted_email=encrypt_email(email),
            email_fingerprint=email_fingerprint(email),
            token_lookup_hash=token_lookup_hash(legacy_token),
            token_hash=make_password(legacy_token),
            expires_at=timezone.now() + timezone.timedelta(minutes=30),
        )

        response = self.client.post('/api/auth/email/confirm/', {
            'token': legacy_token,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.email, 'changed-token@example.com')
        self.assertTrue(user.is_email_verified)

    @patch(
        'ethereum_auth.email_verification._generate_verification_code',
        new=Mock(return_value='890123'),
    )
    @patch('ethereum_auth.email_verification.validate_email')
    @patch('ethereum_auth.email_verification.requests.post')
    def test_existing_user_reused_token_fails(
        self,
        mock_post,
        mock_validate_email,
    ):
        user = User.objects.create_user(
            email='old-reuse@example.com',
            password='testpass123',
            address='0x2222222222222222222222222222222222222222',
            is_email_verified=False,
        )
        self._authenticate(user)
        mock_post.return_value = Mock(json=lambda: {'success': True, 'hostname': 'localhost'})
        mock_validate_email.return_value = self._valid_email_result('changed-reuse@example.com')

        response = self.client.post('/api/auth/email/start/', {
            'email': 'changed-reuse@example.com',
            'turnstile_token': 'ok-token',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post('/api/auth/email/confirm/', {
            'code': '890123',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post('/api/auth/email/confirm/', {
            'code': '890123',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
