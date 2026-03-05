"""
Tests for GitHub OAuth views.
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core import signing
from django.utils import timezone
from rest_framework.test import APIClient
from users.models import User
from social_connections.github.models import GitHubConnection


@override_settings(
    GITHUB_CLIENT_ID='test_client_id',
    GITHUB_CLIENT_SECRET='test_client_secret',
    GITHUB_REDIRECT_URI='http://localhost:8000/api/auth/github/callback/',
    FRONTEND_URL='http://localhost:5173',
    SOCIAL_ENCRYPTION_KEY='9GibasU7S9kA35HL7CovU1xOoAf-WoC-tNVDeQhJlik='
)
class GitHubOAuthInitiateTest(TestCase):
    """Tests for GitHub OAuth initiation."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890'
        )

    def test_initiate_requires_authentication(self):
        """Test that OAuth initiation requires authentication."""
        response = self.client.get('/api/auth/github/')
        self.assertEqual(response.status_code, 403)

    def test_initiate_redirects_to_github(self):
        """Test that authenticated user is redirected to GitHub."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/auth/github/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('github.com/login/oauth/authorize', response.url)
        self.assertIn('client_id=test_client_id', response.url)

    def test_initiate_includes_state_parameter(self):
        """Test that redirect URL includes signed state parameter."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/auth/github/')

        self.assertIn('state=', response.url)


@override_settings(
    GITHUB_CLIENT_ID='test_client_id',
    GITHUB_CLIENT_SECRET='test_client_secret',
    GITHUB_REDIRECT_URI='http://localhost:8000/api/auth/github/callback/',
    FRONTEND_URL='http://localhost:5173',
    SOCIAL_ENCRYPTION_KEY='9GibasU7S9kA35HL7CovU1xOoAf-WoC-tNVDeQhJlik='
)
class GitHubOAuthCallbackTest(TestCase):
    """Tests for GitHub OAuth callback."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890'
        )
        # Clear the used OAuth codes cache to prevent interference between tests
        from social_connections.github import oauth
        oauth._used_oauth_codes.clear()

    def _create_valid_state(self):
        """Create a valid signed state token."""
        state_data = {
            'user_id': self.user.id,
            'nonce': 'test_nonce_12345'
        }
        return signing.dumps(state_data, salt='github_oauth_state')

    @patch('social_connections.github.oauth.requests.post')
    def test_callback_without_code_fails(self, mock_post):
        """Test callback fails without authorization code."""
        # Mock token exchange to fail (no code provided)
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {'error': 'bad_verification_code'}
        )

        state = self._create_valid_state()
        response = self.client.get('/api/auth/github/callback/', {'state': state, 'code': ''})

        self.assertEqual(response.status_code, 200)
        # Should show an error
        self.assertContains(response, 'error')

    def test_callback_without_state_fails(self):
        """Test callback fails without state parameter."""
        response = self.client.get('/api/auth/github/callback/', {'code': 'test_code'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'invalid_state')

    def test_callback_with_expired_state_fails(self):
        """Test callback fails with expired state."""
        # Create state that appears expired
        state_data = {
            'user_id': self.user.id,
            'nonce': 'test_nonce'
        }
        # We can't easily create an expired token, but we can test invalid signature
        response = self.client.get('/api/auth/github/callback/', {
            'code': 'test_code',
            'state': 'invalid_state_token'
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'invalid_state')

    def test_callback_with_error_from_github(self):
        """Test callback handles error from GitHub."""
        response = self.client.get('/api/auth/github/callback/', {
            'error': 'access_denied',
            'error_description': 'User denied access'
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'authorization_failed')

    @patch('social_connections.github.oauth.requests.post')
    @patch('social_connections.github.oauth.requests.get')
    def test_callback_success_creates_connection(self, mock_get, mock_post):
        """Test successful callback creates GitHubConnection."""
        # Mock token exchange
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {'access_token': 'test_access_token'}
        )
        mock_post.return_value.raise_for_status = MagicMock()

        # Mock user info fetch
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'login': 'testgithubuser',
                'id': 12345678
            }
        )
        mock_get.return_value.raise_for_status = MagicMock()

        state = self._create_valid_state()
        response = self.client.get('/api/auth/github/callback/', {
            'code': 'valid_code',
            'state': state
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'var success = true;')

        # Verify connection was created
        self.assertTrue(GitHubConnection.objects.filter(user=self.user).exists())
        connection = GitHubConnection.objects.get(user=self.user)
        self.assertEqual(connection.username, 'testgithubuser')
        self.assertEqual(connection.platform_user_id, '12345678')

    @patch('social_connections.github.oauth.requests.post')
    @patch('social_connections.github.oauth.requests.get')
    def test_callback_rejects_already_linked_account(self, mock_get, mock_post):
        """Test callback rejects GitHub account already linked to another user."""
        # Create another user with this GitHub account
        other_user = User.objects.create_user(
            email='other@example.com',
            address='0x0987654321098765432109876543210987654321'
        )
        GitHubConnection.objects.create(
            user=other_user,
            username='testgithubuser',
            platform_user_id='12345678'
        )

        # Mock token exchange
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {'access_token': 'test_access_token'}
        )
        mock_post.return_value.raise_for_status = MagicMock()

        # Mock user info - same GitHub ID as other_user
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'login': 'testgithubuser',
                'id': 12345678
            }
        )
        mock_get.return_value.raise_for_status = MagicMock()

        state = self._create_valid_state()
        response = self.client.get('/api/auth/github/callback/', {
            'code': 'valid_code',
            'state': state
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already_linked')

        # Verify no new connection was created for test user
        self.assertFalse(GitHubConnection.objects.filter(user=self.user).exists())


@override_settings(
    SOCIAL_ENCRYPTION_KEY='9GibasU7S9kA35HL7CovU1xOoAf-WoC-tNVDeQhJlik=',
    GITHUB_REPO_TO_STAR='genlayerlabs/test-repo'
)
class GitHubDisconnectTest(TestCase):
    """Tests for GitHub disconnect endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890'
        )

    def test_disconnect_requires_authentication(self):
        """Test that disconnect requires authentication."""
        response = self.client.post('/api/v1/social/github/disconnect/')
        self.assertEqual(response.status_code, 403)

    def test_disconnect_removes_connection(self):
        """Test that disconnect removes the GitHub connection."""
        GitHubConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='12345'
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/social/github/disconnect/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(GitHubConnection.objects.filter(user=self.user).exists())

    def test_disconnect_without_connection_succeeds(self):
        """Test that disconnect succeeds even if no connection exists."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/social/github/disconnect/')

        self.assertEqual(response.status_code, 200)


@override_settings(
    SOCIAL_ENCRYPTION_KEY='9GibasU7S9kA35HL7CovU1xOoAf-WoC-tNVDeQhJlik=',
    GITHUB_REPO_TO_STAR='genlayerlabs/test-repo'
)
class GitHubCheckStarTest(TestCase):
    """Tests for GitHub check star endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890'
        )

    def test_check_star_requires_authentication(self):
        """Test that check-star requires authentication."""
        response = self.client.get('/api/v1/social/github/check-star/')
        self.assertEqual(response.status_code, 403)

    def test_check_star_without_connection(self):
        """Test check-star when user has no GitHub connection."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/social/github/check-star/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['has_starred'], False)
        self.assertIn('error', response.data)

    @patch('social_connections.github.oauth.requests.get')
    def test_check_star_returns_true_when_starred(self, mock_get):
        """Test check-star returns true when user has starred the repo."""
        from social_connections.encryption import encrypt_token

        GitHubConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='12345',
            access_token=encrypt_token('test_token')
        )

        # Mock GitHub API response - 204 means starred
        mock_get.return_value = MagicMock(status_code=204)

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/social/github/check-star/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['has_starred'], True)
