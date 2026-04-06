from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory, override_settings
from django.utils import timezone
from rest_framework.test import force_authenticate

from users.models import User
from social_connections.models import GitHubConnection
from social_connections.github_oauth import github_oauth_initiate, disconnect_github, check_repo_star
from social_connections.oauth_service import GitHubOAuthService

TEST_ENCRYPTION_KEY = 'dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXQ='


@override_settings(
    GITHUB_CLIENT_ID='test_client_id',
    GITHUB_CLIENT_SECRET='test_client_secret',
    GITHUB_REDIRECT_URI='http://localhost:8000/api/auth/github/callback/',
    GITHUB_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY,
    SOCIAL_ENCRYPTION_KEY='',
    GITHUB_REPO_TO_STAR='owner/repo',
    FRONTEND_URL='http://localhost:5173',
    ALLOWED_HOSTS=['testserver', 'localhost'],
)
class GitHubOAuthTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            name='Test User',
        )
        self.service = GitHubOAuthService()

    def test_initiate_requires_auth(self):
        request = self.factory.get('/api/auth/github/')
        request.user = None
        # DRF permission should reject unauthenticated
        response = github_oauth_initiate(request)
        self.assertIn(response.status_code, [401, 403])

    def test_initiate_redirects_to_github(self):
        request = self.factory.get('/api/auth/github/')
        force_authenticate(request, user=self.user)
        response = github_oauth_initiate(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('github.com/login/oauth/authorize', response.url)
        self.assertIn('test_client_id', response.url)

    def test_disconnect_deletes_connection(self):
        GitHubConnection.objects.create(
            user=self.user,
            platform_user_id='12345',
            platform_username='testuser',
            linked_at=timezone.now(),
        )
        request = self.factory.post('/api/v1/users/github/disconnect/')
        force_authenticate(request, user=self.user)
        response = disconnect_github(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(GitHubConnection.objects.filter(user=self.user).exists())

    def test_disconnect_no_connection(self):
        request = self.factory.post('/api/v1/users/github/disconnect/')
        force_authenticate(request, user=self.user)
        response = disconnect_github(request)
        self.assertEqual(response.status_code, 200)

    @patch('social_connections.oauth_service.requests')
    def test_check_repo_star_no_connection(self, mock_requests):
        request = self.factory.get('/api/v1/users/github/check-star/')
        force_authenticate(request, user=self.user)
        response = check_repo_star(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['has_starred'])

    @patch('social_connections.oauth_service.requests')
    def test_callback_full_flow(self, mock_requests):
        """Test the full OAuth callback flow with mocked HTTP."""
        # Generate a valid state token
        state = self.service.generate_state(self.user.id)

        # Mock token exchange
        mock_token_response = MagicMock()
        mock_token_response.raise_for_status = MagicMock()
        mock_token_response.json.return_value = {'access_token': 'test_token'}

        # Mock user info
        mock_user_response = MagicMock()
        mock_user_response.raise_for_status = MagicMock()
        mock_user_response.json.return_value = {'id': 12345, 'login': 'ghuser'}

        mock_requests.post.return_value = mock_token_response
        mock_requests.get.return_value = mock_user_response

        from social_connections.github_oauth import github_oauth_callback
        request = self.factory.get('/api/auth/github/callback/', {
            'code': 'test_code',
            'state': state,
        })
        response = github_oauth_callback(request)
        self.assertEqual(response.status_code, 200)

        # Verify connection was created
        conn = GitHubConnection.objects.get(user=self.user)
        self.assertEqual(conn.platform_username, 'ghuser')
        self.assertEqual(conn.platform_user_id, '12345')

    def test_callback_duplicate_code(self):
        """Test that a duplicate code is rejected."""
        state = self.service.generate_state(self.user.id)

        from social_connections.github_oauth import github_oauth_callback
        from social_connections.models import UsedOAuthCode
        UsedOAuthCode.mark_used('duplicate_code', 'github')

        request = self.factory.get('/api/auth/github/callback/', {
            'code': 'duplicate_code',
            'state': state,
        })
        response = github_oauth_callback(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'code_already_used', response.content)

    @patch('social_connections.oauth_service.requests')
    def test_callback_already_linked_to_another_user(self, mock_requests):
        """Test that a GitHub account already linked to another user is rejected."""
        user2 = User.objects.create_user(
            email='other@example.com', password='testpass123', name='Other',
        )
        GitHubConnection.objects.create(
            user=user2,
            platform_user_id='12345',
            platform_username='ghuser',
            linked_at=timezone.now(),
        )

        state = self.service.generate_state(self.user.id)

        mock_token_response = MagicMock()
        mock_token_response.raise_for_status = MagicMock()
        mock_token_response.json.return_value = {'access_token': 'test_token'}

        mock_user_response = MagicMock()
        mock_user_response.raise_for_status = MagicMock()
        mock_user_response.json.return_value = {'id': 12345, 'login': 'ghuser'}

        mock_requests.post.return_value = mock_token_response
        mock_requests.get.return_value = mock_user_response

        from social_connections.github_oauth import github_oauth_callback
        request = self.factory.get('/api/auth/github/callback/', {
            'code': 'new_code_123',
            'state': state,
        })
        response = github_oauth_callback(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'already_linked', response.content)
