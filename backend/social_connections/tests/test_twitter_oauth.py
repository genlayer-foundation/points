"""
Tests for Twitter OAuth views.
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client, override_settings
from django.core import signing
from rest_framework.test import APIClient
from users.models import User
from social_connections.twitter.models import TwitterConnection


@override_settings(
    TWITTER_CLIENT_ID='test_client_id',
    TWITTER_CLIENT_SECRET='test_client_secret',
    TWITTER_REDIRECT_URI='http://localhost:8000/api/auth/twitter/callback/',
    FRONTEND_URL='http://localhost:5173',
    SOCIAL_ENCRYPTION_KEY='9GibasU7S9kA35HL7CovU1xOoAf-WoC-tNVDeQhJlik='
)
class TwitterOAuthInitiateTest(TestCase):
    """Tests for Twitter OAuth initiation."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890'
        )

    def test_initiate_requires_authentication(self):
        """Test that OAuth initiation requires authentication."""
        response = self.client.get('/api/auth/twitter/')
        self.assertEqual(response.status_code, 403)

    def test_initiate_redirects_to_twitter(self):
        """Test that authenticated user is redirected to Twitter."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/auth/twitter/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('twitter.com', response.url)
        self.assertIn('client_id=test_client_id', response.url)

    def test_initiate_includes_pkce_parameters(self):
        """Test that redirect URL includes PKCE code challenge."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/auth/twitter/')

        self.assertIn('code_challenge=', response.url)
        self.assertIn('code_challenge_method=S256', response.url)

    def test_initiate_includes_correct_scopes(self):
        """Test that redirect URL includes required scopes."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/auth/twitter/')

        # URL-encoded scopes
        self.assertIn('scope=', response.url)


@override_settings(
    TWITTER_CLIENT_ID='test_client_id',
    TWITTER_CLIENT_SECRET='test_client_secret',
    TWITTER_REDIRECT_URI='http://localhost:8000/api/auth/twitter/callback/',
    FRONTEND_URL='http://localhost:5173',
    SOCIAL_ENCRYPTION_KEY='9GibasU7S9kA35HL7CovU1xOoAf-WoC-tNVDeQhJlik='
)
class TwitterOAuthCallbackTest(TestCase):
    """Tests for Twitter OAuth callback."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890'
        )
        # Clear the used OAuth codes cache to prevent interference between tests
        from social_connections.twitter import oauth
        oauth._used_oauth_codes.clear()

    def _create_valid_state(self):
        """Create a valid signed state token with PKCE code verifier."""
        state_data = {
            'user_id': self.user.id,
            'code_verifier': 'test_code_verifier_12345678901234567890',
            'nonce': 'test_nonce_12345'
        }
        return signing.dumps(state_data, salt='twitter_oauth_state')

    @patch('social_connections.twitter.oauth.requests.post')
    def test_callback_without_code_fails(self, mock_post):
        """Test callback fails without authorization code."""
        # Mock token exchange to fail
        mock_post.return_value = MagicMock(
            status_code=400,
            json=lambda: {'error': 'invalid_request'}
        )

        state = self._create_valid_state()
        response = self.client.get('/api/auth/twitter/callback/', {'state': state, 'code': ''})

        self.assertEqual(response.status_code, 200)
        # Should show an error
        self.assertContains(response, 'error')

    def test_callback_without_state_fails(self):
        """Test callback fails without state parameter."""
        response = self.client.get('/api/auth/twitter/callback/', {'code': 'test_code'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'invalid_state')

    def test_callback_with_error_from_twitter(self):
        """Test callback handles error from Twitter."""
        response = self.client.get('/api/auth/twitter/callback/', {
            'error': 'access_denied',
            'error_description': 'User denied access'
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'authorization_failed')

    @patch('social_connections.twitter.oauth.requests.post')
    @patch('social_connections.twitter.oauth.requests.get')
    def test_callback_success_creates_connection(self, mock_get, mock_post):
        """Test successful callback creates TwitterConnection."""
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
                'data': {
                    'username': 'testtwitteruser',
                    'id': '987654321'
                }
            }
        )
        mock_get.return_value.raise_for_status = MagicMock()

        state = self._create_valid_state()
        response = self.client.get('/api/auth/twitter/callback/', {
            'code': 'valid_code',
            'state': state
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'var success = true;')

        # Verify connection was created
        self.assertTrue(TwitterConnection.objects.filter(user=self.user).exists())
        connection = TwitterConnection.objects.get(user=self.user)
        self.assertEqual(connection.username, 'testtwitteruser')
        self.assertEqual(connection.platform_user_id, '987654321')

    @patch('social_connections.twitter.oauth.requests.post')
    @patch('social_connections.twitter.oauth.requests.get')
    def test_callback_rejects_already_linked_account(self, mock_get, mock_post):
        """Test callback rejects Twitter account already linked to another user."""
        # Create another user with this Twitter account
        other_user = User.objects.create_user(
            email='other@example.com',
            address='0x0987654321098765432109876543210987654321'
        )
        TwitterConnection.objects.create(
            user=other_user,
            username='testtwitteruser',
            platform_user_id='987654321'
        )

        # Mock token exchange
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'access_token': 'test_access_token',
                'refresh_token': 'test_refresh_token'
            }
        )

        # Mock user info - same Twitter ID as other_user
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'data': {
                    'username': 'testtwitteruser',
                    'id': '987654321'
                }
            }
        )
        mock_get.return_value.raise_for_status = MagicMock()

        state = self._create_valid_state()
        response = self.client.get('/api/auth/twitter/callback/', {
            'code': 'valid_code',
            'state': state
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already_linked')

        # Verify no new connection was created for test user
        self.assertFalse(TwitterConnection.objects.filter(user=self.user).exists())


@override_settings(
    SOCIAL_ENCRYPTION_KEY='9GibasU7S9kA35HL7CovU1xOoAf-WoC-tNVDeQhJlik='
)
class TwitterDisconnectTest(TestCase):
    """Tests for Twitter disconnect endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890'
        )

    def test_disconnect_requires_authentication(self):
        """Test that disconnect requires authentication."""
        response = self.client.post('/api/v1/social/twitter/disconnect/')
        self.assertEqual(response.status_code, 403)

    def test_disconnect_removes_connection(self):
        """Test that disconnect removes the Twitter connection."""
        TwitterConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='12345'
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/social/twitter/disconnect/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(TwitterConnection.objects.filter(user=self.user).exists())

    def test_disconnect_without_connection_succeeds(self):
        """Test that disconnect succeeds even if no connection exists."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/social/twitter/disconnect/')

        self.assertEqual(response.status_code, 200)
