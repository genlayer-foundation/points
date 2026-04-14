from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.core import signing

from social_connections.oauth_service import GitHubOAuthService, TwitterOAuthService, DiscordOAuthService
from social_connections.encryption import encrypt_token, decrypt_token
from social_connections.models import UsedOAuthCode

TEST_ENCRYPTION_KEY = 'dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXQ='  # base64 32 bytes


@override_settings(SOCIAL_ENCRYPTION_KEY='', GITHUB_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY)
class EncryptionTest(TestCase):
    def test_encrypt_decrypt_roundtrip(self):
        token = 'my_secret_token_12345'
        encrypted = encrypt_token(token)
        self.assertNotEqual(encrypted, token)
        decrypted = decrypt_token(encrypted)
        self.assertEqual(decrypted, token)

    def test_empty_token(self):
        self.assertEqual(encrypt_token(''), '')
        self.assertEqual(decrypt_token(''), '')

    def test_different_tokens_different_ciphertext(self):
        enc1 = encrypt_token('token1')
        enc2 = encrypt_token('token2')
        self.assertNotEqual(enc1, enc2)


class GitHubOAuthServiceTest(TestCase):
    def setUp(self):
        self.service = GitHubOAuthService()

    def test_generate_and_validate_state(self):
        state = self.service.generate_state(42)
        data = self.service.validate_state(state)
        self.assertEqual(data['user_id'], 42)
        self.assertIn('nonce', data)

    def test_state_with_extra_data(self):
        state = self.service.generate_state(42, extra_data={'foo': 'bar'})
        data = self.service.validate_state(state)
        self.assertEqual(data['foo'], 'bar')

    def test_invalid_state_signature(self):
        with self.assertRaises(signing.BadSignature):
            self.service.validate_state('tampered_state_token')

    def test_expired_state(self):
        state = signing.dumps({'user_id': 1, 'nonce': 'x'}, salt='github_oauth_state')
        # Force expire by using a different max_age
        with self.assertRaises(signing.SignatureExpired):
            signing.loads(state, salt='github_oauth_state', max_age=-1)

    def test_mark_code_used(self):
        self.assertTrue(self.service.mark_code_used('code123'))
        self.assertFalse(self.service.mark_code_used('code123'))
        # Different code should work
        self.assertTrue(self.service.mark_code_used('code456'))


class TwitterOAuthServiceTest(TestCase):
    def setUp(self):
        self.service = TwitterOAuthService()

    def test_pkce_code_verifier(self):
        verifier = self.service.generate_code_verifier()
        self.assertTrue(len(verifier) <= 128)
        self.assertTrue(len(verifier) >= 43)

    def test_pkce_code_challenge(self):
        verifier = 'test_verifier_string'
        challenge = self.service.generate_code_challenge(verifier)
        self.assertNotEqual(challenge, verifier)
        # S256 challenge should be base64url encoded
        self.assertNotIn('=', challenge)

    def test_state_embeds_code_verifier(self):
        verifier = self.service.generate_code_verifier()
        state = self.service.generate_state(1, extra_data={'code_verifier': verifier})
        data = self.service.validate_state(state)
        self.assertEqual(data['code_verifier'], verifier)

    def test_platform_name(self):
        self.assertEqual(self.service.platform_name, 'twitter')

    def test_uses_pkce(self):
        self.assertTrue(self.service.uses_pkce)


class DiscordOAuthServiceTest(TestCase):
    def setUp(self):
        self.service = DiscordOAuthService()

    def test_platform_name(self):
        self.assertEqual(self.service.platform_name, 'discord')

    def test_scopes(self):
        self.assertIn('identify', self.service.scopes)
        self.assertIn('guilds.members.read', self.service.scopes)

    @patch('social_connections.oauth_service.requests')
    def test_check_guild_membership_member(self, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response

        result = self.service.check_guild_membership('token', 'guild_id')
        self.assertTrue(result)

    @patch('social_connections.oauth_service.requests')
    def test_check_guild_membership_not_member(self, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response

        result = self.service.check_guild_membership('token', 'guild_id')
        self.assertFalse(result)

    @patch('social_connections.oauth_service.requests')
    def test_check_guild_membership_unauthorized(self, mock_requests):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_requests.get.return_value = mock_response

        result = self.service.check_guild_membership('token', 'guild_id')
        self.assertFalse(result)
