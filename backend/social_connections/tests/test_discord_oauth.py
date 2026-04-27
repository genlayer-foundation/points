from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory, override_settings
from django.utils import timezone
from rest_framework.test import force_authenticate

from users.models import User
from social_connections.models import DiscordConnection
from social_connections.discord_oauth import (
    discord_oauth_initiate, disconnect_discord, check_discord_guild,
)
from social_connections.oauth_service import DiscordOAuthService

TEST_ENCRYPTION_KEY = 'dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXQ='


@override_settings(
    DISCORD_CLIENT_ID='test_discord_id',
    DISCORD_CLIENT_SECRET='test_discord_secret',
    DISCORD_REDIRECT_URI='http://localhost:8000/api/auth/discord/callback/',
    DISCORD_GUILD_ID='test_guild_123',
    GITHUB_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY,
    SOCIAL_ENCRYPTION_KEY='',
    FRONTEND_URL='http://localhost:5173',
    ALLOWED_HOSTS=['testserver', 'localhost'],
)
class DiscordOAuthTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            name='Test User',
        )
        self.service = DiscordOAuthService()

    def test_initiate_requires_auth(self):
        request = self.factory.get('/api/auth/discord/')
        request.user = None
        response = discord_oauth_initiate(request)
        self.assertIn(response.status_code, [401, 403])

    def test_initiate_redirects_to_discord(self):
        request = self.factory.get('/api/auth/discord/')
        force_authenticate(request, user=self.user)
        response = discord_oauth_initiate(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('discord.com/oauth2/authorize', response.url)
        self.assertIn('test_discord_id', response.url)

    def test_disconnect_deletes_connection(self):
        DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='11111',
            platform_username='discorduser',
            linked_at=timezone.now(),
        )
        request = self.factory.post('/api/v1/users/discord/disconnect/')
        force_authenticate(request, user=self.user)
        response = disconnect_discord(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(DiscordConnection.objects.filter(user=self.user).exists())

    def test_disconnect_no_connection(self):
        request = self.factory.post('/api/v1/users/discord/disconnect/')
        force_authenticate(request, user=self.user)
        response = disconnect_discord(request)
        self.assertEqual(response.status_code, 200)

    @patch('social_connections.oauth_service.requests')
    def test_callback_full_flow(self, mock_requests):
        """Test the full Discord OAuth callback flow."""
        state = self.service.generate_state(self.user.id)

        mock_token_response = MagicMock()
        mock_token_response.raise_for_status = MagicMock()
        mock_token_response.json.return_value = {'access_token': 'discord_token'}

        mock_user_response = MagicMock()
        mock_user_response.raise_for_status = MagicMock()
        mock_user_response.json.return_value = {
            'id': '11111',
            'username': 'discorduser',
            'discriminator': '1234',
            'avatar': 'abc123hash',
        }

        mock_requests.post.return_value = mock_token_response
        mock_requests.get.return_value = mock_user_response

        from social_connections.discord_oauth import discord_oauth_callback
        request = self.factory.get('/api/auth/discord/callback/', {
            'code': 'discord_code_123',
            'state': state,
        })
        response = discord_oauth_callback(request)
        self.assertEqual(response.status_code, 200)

        conn = DiscordConnection.objects.get(user=self.user)
        self.assertEqual(conn.platform_username, 'discorduser')
        self.assertEqual(conn.platform_user_id, '11111')
        self.assertEqual(conn.discriminator, '1234')
        self.assertEqual(conn.avatar_hash, 'abc123hash')

    @patch('social_connections.oauth_service.requests')
    def test_callback_without_optional_fields(self, mock_requests):
        """Test callback when discriminator and avatar are missing."""
        state = self.service.generate_state(self.user.id)

        mock_token_response = MagicMock()
        mock_token_response.raise_for_status = MagicMock()
        mock_token_response.json.return_value = {'access_token': 'discord_token'}

        mock_user_response = MagicMock()
        mock_user_response.raise_for_status = MagicMock()
        mock_user_response.json.return_value = {
            'id': '11111',
            'username': 'discorduser',
        }

        mock_requests.post.return_value = mock_token_response
        mock_requests.get.return_value = mock_user_response

        from social_connections.discord_oauth import discord_oauth_callback
        request = self.factory.get('/api/auth/discord/callback/', {
            'code': 'discord_code_no_extras',
            'state': state,
        })
        response = discord_oauth_callback(request)
        self.assertEqual(response.status_code, 200)

        conn = DiscordConnection.objects.get(user=self.user)
        self.assertEqual(conn.discriminator, '')
        self.assertEqual(conn.avatar_hash, '')

    def test_callback_duplicate_code(self):
        """Test that a duplicate code is rejected."""
        state = self.service.generate_state(self.user.id)

        from social_connections.discord_oauth import discord_oauth_callback
        from social_connections.models import UsedOAuthCode
        UsedOAuthCode.mark_used('dup_discord_code', 'discord')

        request = self.factory.get('/api/auth/discord/callback/', {
            'code': 'dup_discord_code',
            'state': state,
        })
        response = discord_oauth_callback(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'code_already_used', response.content)

    @patch('social_connections.oauth_service.requests')
    def test_callback_already_linked_to_another_user(self, mock_requests):
        """Test that a Discord account already linked to another user is rejected."""
        user2 = User.objects.create_user(
            email='other@example.com', password='testpass123', name='Other',
        )
        DiscordConnection.objects.create(
            user=user2,
            platform_user_id='11111',
            platform_username='discorduser',
            linked_at=timezone.now(),
        )

        state = self.service.generate_state(self.user.id)

        mock_token_response = MagicMock()
        mock_token_response.raise_for_status = MagicMock()
        mock_token_response.json.return_value = {'access_token': 'discord_token'}

        mock_user_response = MagicMock()
        mock_user_response.raise_for_status = MagicMock()
        mock_user_response.json.return_value = {
            'id': '11111',
            'username': 'discorduser',
        }

        mock_requests.post.return_value = mock_token_response
        mock_requests.get.return_value = mock_user_response

        from social_connections.discord_oauth import discord_oauth_callback
        request = self.factory.get('/api/auth/discord/callback/', {
            'code': 'new_discord_code_456',
            'state': state,
        })
        response = discord_oauth_callback(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'already_linked', response.content)

    @patch('social_connections.oauth_service.requests')
    def test_check_guild_no_connection(self, mock_requests):
        """Test guild check when user has no Discord connection."""
        request = self.factory.get('/api/v1/users/discord/check-guild/')
        force_authenticate(request, user=self.user)
        response = check_discord_guild(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['is_member'])

    @patch('social_connections.discord_oauth.service.check_guild_membership')
    def test_check_guild_is_member(self, mock_check):
        """Test guild check when user is a member."""
        from social_connections.encryption import encrypt_token
        DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='11111',
            platform_username='discorduser',
            access_token=encrypt_token('test_token'),
            linked_at=timezone.now(),
        )
        mock_check.return_value = True

        request = self.factory.get('/api/v1/users/discord/check-guild/')
        force_authenticate(request, user=self.user)
        response = check_discord_guild(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_member'])

        # Verify result was cached
        conn = DiscordConnection.objects.get(user=self.user)
        self.assertTrue(conn.guild_member)
        self.assertIsNotNone(conn.guild_checked_at)

    @patch('social_connections.discord_oauth.service.check_guild_membership')
    def test_check_guild_not_member(self, mock_check):
        """Test guild check when user is not a member."""
        from social_connections.encryption import encrypt_token
        DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='11111',
            platform_username='discorduser',
            access_token=encrypt_token('test_token'),
            linked_at=timezone.now(),
        )
        mock_check.return_value = False

        request = self.factory.get('/api/v1/users/discord/check-guild/')
        force_authenticate(request, user=self.user)
        response = check_discord_guild(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['is_member'])
