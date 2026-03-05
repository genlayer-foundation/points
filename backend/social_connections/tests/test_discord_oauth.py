"""
Tests for Discord OAuth views.
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client, override_settings
from django.core import signing
from rest_framework.test import APIClient
from users.models import User
from social_connections.discord.models import DiscordConnection


@override_settings(
    DISCORD_CLIENT_ID='test_client_id',
    DISCORD_CLIENT_SECRET='test_client_secret',
    DISCORD_REDIRECT_URI='http://localhost:8000/api/auth/discord/callback/',
    DISCORD_GUILD_ID='123456789',
    FRONTEND_URL='http://localhost:5173',
    SOCIAL_ENCRYPTION_KEY='9GibasU7S9kA35HL7CovU1xOoAf-WoC-tNVDeQhJlik='
)
class DiscordOAuthInitiateTest(TestCase):
    """Tests for Discord OAuth initiation."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890'
        )

    def test_initiate_requires_authentication(self):
        """Test that OAuth initiation requires authentication."""
        response = self.client.get('/api/auth/discord/')
        self.assertEqual(response.status_code, 403)

    def test_initiate_redirects_to_discord(self):
        """Test that authenticated user is redirected to Discord."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/auth/discord/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('discord.com', response.url)
        self.assertIn('client_id=test_client_id', response.url)

    def test_initiate_includes_correct_scopes(self):
        """Test that redirect URL includes required scopes."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/auth/discord/')

        # URL-encoded scopes
        self.assertIn('scope=', response.url)
        # identify and guilds scopes
        self.assertIn('identify', response.url)
        self.assertIn('guilds', response.url)


@override_settings(
    DISCORD_CLIENT_ID='test_client_id',
    DISCORD_CLIENT_SECRET='test_client_secret',
    DISCORD_REDIRECT_URI='http://localhost:8000/api/auth/discord/callback/',
    DISCORD_GUILD_ID='123456789',
    FRONTEND_URL='http://localhost:5173',
    SOCIAL_ENCRYPTION_KEY='9GibasU7S9kA35HL7CovU1xOoAf-WoC-tNVDeQhJlik='
)
class DiscordOAuthCallbackTest(TestCase):
    """Tests for Discord OAuth callback."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890'
        )
        # Clear the used OAuth codes cache to prevent interference between tests
        from social_connections.discord import oauth
        oauth._used_oauth_codes.clear()

    def _create_valid_state(self):
        """Create a valid signed state token."""
        state_data = {
            'user_id': self.user.id,
            'nonce': 'test_nonce_12345'
        }
        return signing.dumps(state_data, salt='discord_oauth_state')

    @patch('social_connections.discord.oauth.requests.post')
    def test_callback_without_code_fails(self, mock_post):
        """Test callback fails without authorization code."""
        # Mock token exchange to fail
        mock_post.return_value = MagicMock(
            status_code=400,
            json=lambda: {'error': 'invalid_request'}
        )

        state = self._create_valid_state()
        response = self.client.get('/api/auth/discord/callback/', {'state': state, 'code': ''})

        self.assertEqual(response.status_code, 200)
        # Should show an error
        self.assertContains(response, 'error')

    def test_callback_without_state_fails(self):
        """Test callback fails without state parameter."""
        response = self.client.get('/api/auth/discord/callback/', {'code': 'test_code'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'invalid_state')

    def test_callback_with_error_from_discord(self):
        """Test callback handles error from Discord."""
        response = self.client.get('/api/auth/discord/callback/', {
            'error': 'access_denied',
            'error_description': 'User denied access'
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'authorization_failed')

    @patch('social_connections.discord.oauth.requests.post')
    @patch('social_connections.discord.oauth.requests.get')
    def test_callback_success_creates_connection(self, mock_get, mock_post):
        """Test successful callback creates DiscordConnection."""
        # Mock token exchange
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'access_token': 'test_access_token',
                'refresh_token': 'test_refresh_token'
            }
        )

        # Mock user info fetch
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'username': 'testdiscorduser',
                'id': '111222333',
                'discriminator': '1234',
                'avatar': 'abc123hash'
            }
        )
        mock_get.return_value.raise_for_status = MagicMock()

        state = self._create_valid_state()
        response = self.client.get('/api/auth/discord/callback/', {
            'code': 'valid_code',
            'state': state
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'var success = true;')

        # Verify connection was created
        self.assertTrue(DiscordConnection.objects.filter(user=self.user).exists())
        connection = DiscordConnection.objects.get(user=self.user)
        self.assertEqual(connection.username, 'testdiscorduser')
        self.assertEqual(connection.platform_user_id, '111222333')
        self.assertEqual(connection.discriminator, '1234')
        self.assertEqual(connection.avatar_hash, 'abc123hash')

    @patch('social_connections.discord.oauth.requests.post')
    @patch('social_connections.discord.oauth.requests.get')
    def test_callback_rejects_already_linked_account(self, mock_get, mock_post):
        """Test callback rejects Discord account already linked to another user."""
        # Create another user with this Discord account
        other_user = User.objects.create_user(
            email='other@example.com',
            address='0x0987654321098765432109876543210987654321'
        )
        DiscordConnection.objects.create(
            user=other_user,
            username='testdiscorduser',
            platform_user_id='111222333'
        )

        # Mock token exchange
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'access_token': 'test_access_token',
                'refresh_token': 'test_refresh_token'
            }
        )

        # Mock user info - same Discord ID as other_user
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'username': 'testdiscorduser',
                'id': '111222333',
                'discriminator': '1234',
                'avatar': 'abc123hash'
            }
        )
        mock_get.return_value.raise_for_status = MagicMock()

        state = self._create_valid_state()
        response = self.client.get('/api/auth/discord/callback/', {
            'code': 'valid_code',
            'state': state
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already_linked')

        # Verify no new connection was created for test user
        self.assertFalse(DiscordConnection.objects.filter(user=self.user).exists())


@override_settings(
    SOCIAL_ENCRYPTION_KEY='9GibasU7S9kA35HL7CovU1xOoAf-WoC-tNVDeQhJlik=',
    DISCORD_GUILD_ID='123456789'
)
class DiscordDisconnectTest(TestCase):
    """Tests for Discord disconnect endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890'
        )

    def test_disconnect_requires_authentication(self):
        """Test that disconnect requires authentication."""
        response = self.client.post('/api/v1/social/discord/disconnect/')
        self.assertEqual(response.status_code, 403)

    def test_disconnect_removes_connection(self):
        """Test that disconnect removes the Discord connection."""
        DiscordConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='12345'
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/social/discord/disconnect/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(DiscordConnection.objects.filter(user=self.user).exists())

    def test_disconnect_without_connection_succeeds(self):
        """Test that disconnect succeeds even if no connection exists."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/social/discord/disconnect/')

        self.assertEqual(response.status_code, 200)


@override_settings(
    SOCIAL_ENCRYPTION_KEY='9GibasU7S9kA35HL7CovU1xOoAf-WoC-tNVDeQhJlik=',
    DISCORD_GUILD_ID='123456789'
)
class DiscordCheckGuildTest(TestCase):
    """Tests for Discord check-guild endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890'
        )

    def test_check_guild_requires_authentication(self):
        """Test that check-guild requires authentication."""
        response = self.client.get('/api/v1/social/discord/check-guild/')
        self.assertEqual(response.status_code, 403)

    def test_check_guild_without_connection(self):
        """Test check-guild when user has no Discord connection."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/social/discord/check-guild/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['is_member'], False)
        self.assertIn('error', response.data)

    @patch('social_connections.discord.oauth.requests.get')
    def test_check_guild_returns_true_when_member(self, mock_get):
        """Test check-guild returns true when user is a guild member."""
        from social_connections.encryption import encrypt_token

        DiscordConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='12345',
            access_token=encrypt_token('test_token')
        )

        # Mock Discord API response - user's guilds including our guild
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [
                {'id': '111111111', 'name': 'Other Server'},
                {'id': '123456789', 'name': 'Our Server'},  # This is the configured guild
            ]
        )
        mock_get.return_value.raise_for_status = MagicMock()

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/social/discord/check-guild/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['is_member'], True)

    @patch('social_connections.discord.oauth.requests.get')
    def test_check_guild_returns_false_when_not_member(self, mock_get):
        """Test check-guild returns false when user is not a guild member."""
        from social_connections.encryption import encrypt_token

        DiscordConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='12345',
            access_token=encrypt_token('test_token')
        )

        # Mock Discord API response - user's guilds NOT including our guild
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [
                {'id': '111111111', 'name': 'Other Server'},
                {'id': '222222222', 'name': 'Another Server'},
            ]
        )
        mock_get.return_value.raise_for_status = MagicMock()

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/social/discord/check-guild/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['is_member'], False)

    @override_settings(DISCORD_GUILD_ID='')
    def test_check_guild_without_configured_guild(self):
        """Test check-guild when no guild ID is configured."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/social/discord/check-guild/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['is_member'], False)
        self.assertIn('not configured', response.data.get('error', ''))
