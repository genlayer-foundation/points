from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from eth_account import Account
from eth_account.messages import encode_defunct
from rest_framework.test import APIClient

from .models import Nonce


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
