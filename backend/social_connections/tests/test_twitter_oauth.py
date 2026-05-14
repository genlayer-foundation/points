from unittest.mock import patch, MagicMock
from urllib.parse import parse_qs, urlparse

import requests
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TestCase, RequestFactory, override_settings
from django.utils import timezone
from rest_framework.test import force_authenticate

from users.models import User
from social_connections.models import TwitterConnection
from social_connections.encryption import encrypt_token
from social_connections.twitter_oauth import (
    twitter_oauth_initiate,
    disconnect_twitter,
    refresh_twitter_username,
)
from social_connections.oauth_service import TwitterOAuthService

TEST_ENCRYPTION_KEY = 'dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXQ='


@override_settings(
    TWITTER_CLIENT_ID='test_twitter_id',
    TWITTER_CLIENT_SECRET='test_twitter_secret',
    TWITTER_REDIRECT_URI='http://localhost:8000/api/auth/twitter/callback/',
    GITHUB_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY,
    SOCIAL_ENCRYPTION_KEY='',
    FRONTEND_URL='http://localhost:5173',
    ALLOWED_HOSTS=['testserver', 'localhost'],
)
class TwitterOAuthTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            name='Test User',
        )
        self.service = TwitterOAuthService()

    def attach_session(self, request):
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        return request

    def test_initiate_requires_auth(self):
        request = self.factory.get('/api/auth/twitter/')
        request.user = None
        response = twitter_oauth_initiate(request)
        self.assertIn(response.status_code, [401, 403])

    def test_initiate_redirects_to_twitter(self):
        request = self.factory.get('/api/auth/twitter/')
        self.attach_session(request)
        force_authenticate(request, user=self.user)
        response = twitter_oauth_initiate(request)

        query = parse_qs(urlparse(response.url).query)

        self.assertEqual(response.status_code, 302)
        self.assertIn('x.com/i/oauth2/authorize', response.url)
        self.assertEqual(query['client_id'][0], 'test_twitter_id')
        self.assertEqual(query['response_type'][0], 'code')
        self.assertEqual(query['scope'][0], 'tweet.read users.read offline.access')
        self.assertIn('code_challenge', query)
        self.assertEqual(query['code_challenge_method'][0], 'S256')
        self.assertLessEqual(len(query['state'][0]), 500)
        self.assertIn('scope=tweet.read%20users.read%20offline.access', response.url)
        self.assertNotIn('scope=tweet.read+users.read', response.url)
        state_data = self.service.validate_state(query['state'][0])
        self.assertTrue(state_data['code_verifier'])
        self.assertEqual(state_data['redirect_url'], 'http://localhost:5173')

    def test_initiate_validates_redirect_before_storing_in_state(self):
        request = self.factory.get('/api/auth/twitter/', {
            'redirect': 'https://evil.example/profile',
        })
        self.attach_session(request)
        force_authenticate(request, user=self.user)

        response = twitter_oauth_initiate(request)

        query = parse_qs(urlparse(response.url).query)
        state_data = self.service.validate_state(query['state'][0])

        self.assertEqual(response.status_code, 302)
        self.assertEqual(state_data['redirect_url'], 'http://localhost:5173')

    def test_disconnect_deletes_connection(self):
        TwitterConnection.objects.create(
            user=self.user,
            platform_user_id='99999',
            platform_username='twitteruser',
            linked_at=timezone.now(),
        )
        request = self.factory.post('/api/v1/users/twitter/disconnect/')
        force_authenticate(request, user=self.user)
        response = disconnect_twitter(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TwitterConnection.objects.filter(user=self.user).exists())

    def test_disconnect_no_connection(self):
        request = self.factory.post('/api/v1/users/twitter/disconnect/')
        force_authenticate(request, user=self.user)
        response = disconnect_twitter(request)
        self.assertEqual(response.status_code, 200)

    @patch('social_connections.oauth_service.requests')
    def test_callback_full_flow(self, mock_requests):
        """Test the full Twitter OAuth callback flow with PKCE."""
        code_verifier = self.service.generate_code_verifier()
        state = self.service.generate_state(self.user.id, extra_data={
            'code_verifier': code_verifier,
            'redirect_url': 'http://localhost:5173',
        })

        mock_token_response = MagicMock()
        mock_token_response.raise_for_status = MagicMock()
        mock_token_response.json.return_value = {'access_token': 'twitter_token'}

        mock_user_response = MagicMock()
        mock_user_response.raise_for_status = MagicMock()
        mock_user_response.json.return_value = {
            'data': {'id': '99999', 'username': 'twitteruser'},
        }

        mock_requests.post.return_value = mock_token_response
        mock_requests.get.return_value = mock_user_response

        from social_connections.twitter_oauth import twitter_oauth_callback
        request = self.factory.get('/api/auth/twitter/callback/', {
            'code': 'twitter_code_123',
            'state': state,
        })
        response = twitter_oauth_callback(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('oauth_platform=twitter', response.url)
        self.assertIn('oauth_verified=true', response.url)

        conn = TwitterConnection.objects.get(user=self.user)
        self.assertEqual(conn.platform_username, 'twitteruser')
        self.assertEqual(conn.platform_user_id, '99999')
        mock_requests.post.assert_called_once()
        self.assertEqual(mock_requests.post.call_args.kwargs['data']['code_verifier'], code_verifier)

    def test_callback_duplicate_code(self):
        """Test that a duplicate code is rejected."""
        state = self.service.generate_state(self.user.id)

        from social_connections.twitter_oauth import twitter_oauth_callback
        from social_connections.models import UsedOAuthCode
        UsedOAuthCode.mark_used('dup_twitter_code', 'twitter')

        request = self.factory.get('/api/auth/twitter/callback/', {
            'code': 'dup_twitter_code',
            'state': state,
        })
        response = twitter_oauth_callback(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('oauth_platform=twitter', response.url)
        self.assertIn('oauth_verified=false', response.url)
        self.assertIn('oauth_error=code_already_used', response.url)

    @patch('social_connections.oauth_service.requests')
    def test_callback_already_linked_to_another_user(self, mock_requests):
        """Test that a Twitter account already linked to another user is rejected."""
        user2 = User.objects.create_user(
            email='other@example.com', password='testpass123', name='Other',
        )
        TwitterConnection.objects.create(
            user=user2,
            platform_user_id='99999',
            platform_username='twitteruser',
            linked_at=timezone.now(),
        )

        code_verifier = self.service.generate_code_verifier()
        state = self.service.generate_state(self.user.id, extra_data={
            'code_verifier': code_verifier,
            'redirect_url': 'http://localhost:5173',
        })

        mock_token_response = MagicMock()
        mock_token_response.raise_for_status = MagicMock()
        mock_token_response.json.return_value = {'access_token': 'twitter_token'}

        mock_user_response = MagicMock()
        mock_user_response.raise_for_status = MagicMock()
        mock_user_response.json.return_value = {
            'data': {'id': '99999', 'username': 'twitteruser'},
        }

        mock_requests.post.return_value = mock_token_response
        mock_requests.get.return_value = mock_user_response

        from social_connections.twitter_oauth import twitter_oauth_callback
        request = self.factory.get('/api/auth/twitter/callback/', {
            'code': 'new_twitter_code_456',
            'state': state,
        })
        response = twitter_oauth_callback(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('oauth_platform=twitter', response.url)
        self.assertIn('oauth_verified=false', response.url)
        self.assertIn('oauth_error=already_linked', response.url)

    @patch('social_connections.oauth_service.decrypt_token', return_value='test_token')
    @patch('social_connections.oauth_service.requests')
    def test_refresh_twitter_username_updates_existing_connection(self, mock_requests, mock_decrypt_token):
        TwitterConnection.objects.create(
            user=self.user,
            platform_user_id='99999',
            platform_username='old_x_name',
            access_token='encrypted-token',
            linked_at=timezone.now(),
        )

        mock_user_response = MagicMock()
        mock_user_response.raise_for_status = MagicMock()
        mock_user_response.json.return_value = {
            'data': {'id': '99999', 'username': 'new_x_name'},
        }
        mock_requests.get.return_value = mock_user_response

        request = self.factory.post('/api/v1/users/twitter/refresh/')
        force_authenticate(request, user=self.user)
        response = refresh_twitter_username(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['changed'])
        self.assertEqual(response.data['twitter_connection']['platform_username'], 'new_x_name')
        self.assertEqual(self.user.twitterconnection.platform_username, 'new_x_name')

    @patch('social_connections.oauth_service.requests')
    def test_refresh_twitter_username_uses_refresh_token_when_access_token_expired(self, mock_requests):
        TwitterConnection.objects.create(
            user=self.user,
            platform_user_id='99999',
            platform_username='old_x_name',
            access_token=encrypt_token('expired-token'),
            refresh_token=encrypt_token('refresh-token'),
            linked_at=timezone.now(),
        )

        expired_response = MagicMock()
        expired_response.status_code = 401
        expired_error = requests.HTTPError(response=expired_response)
        first_user_response = MagicMock()
        first_user_response.raise_for_status.side_effect = expired_error

        refresh_response = MagicMock()
        refresh_response.raise_for_status = MagicMock()
        refresh_response.json.return_value = {
            'access_token': 'fresh-token',
            'refresh_token': 'new-refresh-token',
        }

        second_user_response = MagicMock()
        second_user_response.raise_for_status = MagicMock()
        second_user_response.json.return_value = {
            'data': {'id': '99999', 'username': 'new_x_name'},
        }

        mock_requests.get.side_effect = [first_user_response, second_user_response]
        mock_requests.post.return_value = refresh_response

        request = self.factory.post('/api/v1/users/twitter/refresh/')
        force_authenticate(request, user=self.user)
        response = refresh_twitter_username(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['changed'])
        self.assertEqual(self.user.twitterconnection.platform_username, 'new_x_name')

    @patch('social_connections.oauth_service.requests')
    def test_refresh_twitter_username_reconnects_when_refresh_token_rejected(self, mock_requests):
        TwitterConnection.objects.create(
            user=self.user,
            platform_user_id='99999',
            platform_username='old_x_name',
            access_token=encrypt_token('expired-token'),
            refresh_token=encrypt_token('revoked-refresh-token'),
            linked_at=timezone.now(),
        )

        expired_response = MagicMock()
        expired_response.status_code = 401
        expired_error = requests.HTTPError(response=expired_response)
        first_user_response = MagicMock()
        first_user_response.raise_for_status.side_effect = expired_error

        rejected_refresh_response = MagicMock()
        rejected_refresh_response.status_code = 400
        rejected_refresh_response.raise_for_status.side_effect = requests.HTTPError(
            response=rejected_refresh_response,
        )

        mock_requests.get.return_value = first_user_response
        mock_requests.post.return_value = rejected_refresh_response

        request = self.factory.post('/api/v1/users/twitter/refresh/')
        force_authenticate(request, user=self.user)
        response = refresh_twitter_username(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'invalid_refresh_token')
        self.assertIn('Please reconnect X', response.data['error'])

    @patch('social_connections.oauth_service.decrypt_token', return_value='test_token')
    @patch('social_connections.oauth_service.requests')
    def test_refresh_twitter_username_rejects_account_mismatch(self, mock_requests, mock_decrypt_token):
        TwitterConnection.objects.create(
            user=self.user,
            platform_user_id='99999',
            platform_username='old_x_name',
            access_token='encrypted-token',
            linked_at=timezone.now(),
        )

        mock_user_response = MagicMock()
        mock_user_response.raise_for_status = MagicMock()
        mock_user_response.json.return_value = {
            'data': {'id': '12345', 'username': 'other_x_name'},
        }
        mock_requests.get.return_value = mock_user_response

        request = self.factory.post('/api/v1/users/twitter/refresh/')
        force_authenticate(request, user=self.user)
        response = refresh_twitter_username(request)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'account_mismatch')
        self.assertEqual(self.user.twitterconnection.platform_username, 'old_x_name')
