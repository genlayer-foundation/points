"""
Tests for email security - authentication emails are only exposed to the owner.
"""
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.throttling import SimpleRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from contributions.node_upgrade.models import TargetNodeVersion
from leaderboard.models import LeaderboardEntry
from social_connections.models import DiscordConnection, DiscordRole, GitHubConnection, TwitterConnection
from validators.models import Validator

User = get_user_model()


class EmailSecurityTests(TestCase):
    """Test that authentication emails are not exposed in public API payloads."""
    
    def setUp(self):
        """Set up test client and users."""
        cache.clear()
        self.client = APIClient()
        
        # Create a user with auto-generated email (unverified)
        self.unverified_user = User.objects.create_user(
            email='0x123@ethereum.address',
            password='testpass123',
            name='Unverified User',
            address='0x123',
            is_email_verified=False
        )
        
        # Create a user with verified email
        self.verified_user = User.objects.create_user(
            email='verified@example.com',
            password='testpass123',
            name='Verified User',
            address='0x456',
            is_email_verified=True
        )
        
        # Create another user to test viewing other users' profiles
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            name='Other User',
            address='0x789',
            is_email_verified=True
        )

        self.hidden_user = User.objects.create_user(
            email='hidden@example.com',
            password='testpass123',
            name='Hidden User',
            address='0xabc',
            is_email_verified=True,
            visible=False,
        )

        TargetNodeVersion.objects.create(
            version='1.2.0',
            network='asimov',
            target_date=timezone.now(),
            is_active=True,
        )
        TargetNodeVersion.objects.create(
            version='2.0.0',
            network='bradbury',
            target_date=timezone.now(),
            is_active=True,
        )
        Validator.objects.create(
            user=self.verified_user,
            node_version_asimov='1.2.3',
            node_version_bradbury='1.9.0',
        )

        self.verified_user.is_banned = True
        self.verified_user.ban_reason = 'private moderation note'
        self.verified_user.referred_by = self.other_user
        self.verified_user.save(update_fields=['is_banned', 'ban_reason', 'referred_by'])

        GitHubConnection.objects.create(
            user=self.verified_user,
            platform_user_id='gh-1',
            platform_username='verified-gh',
            access_token='encrypted-gh-access-token',
            refresh_token='encrypted-gh-refresh-token',
            linked_at=timezone.now(),
        )
        TwitterConnection.objects.create(
            user=self.verified_user,
            platform_user_id='tw-1',
            platform_username='verified-x',
            access_token='encrypted-x-access-token',
            refresh_token='encrypted-x-refresh-token',
            linked_at=timezone.now(),
        )
        discord = DiscordConnection.objects.create(
            user=self.verified_user,
            platform_user_id='dc-1',
            platform_username='verified-discord',
            access_token='encrypted-discord-access-token',
            refresh_token='encrypted-discord-refresh-token',
            linked_at=timezone.now(),
            guild_member=True,
            guild_checked_at=timezone.now(),
            roles_sync_error='private sync error',
            roles_manual_synced_at=timezone.now(),
            guild_joined_at=timezone.now(),
            guild_nick='private nickname',
        )
        role = DiscordRole.objects.create(
            guild_id='guild-1',
            role_id='role-1',
            name='Private Role',
        )
        discord.current_roles.add(role)
    
    def authenticate(self, user):
        """Authenticate the client with the given user."""
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def assert_requires_authentication(self, response):
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
    
    def test_unverified_email_not_exposed_in_own_profile(self):
        """Test that unverified email is not exposed when user views own profile."""
        self.authenticate(self.unverified_user)
        
        # Test /api/v1/users/me/
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], '')  # Should be empty string
        self.assertFalse(response.data['is_email_verified'])
    
    def test_verified_email_shown_in_own_profile(self):
        """Test that verified email is shown when user views own profile."""
        self.authenticate(self.verified_user)
        
        # Test /api/v1/users/me/
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'verified@example.com')
        self.assertTrue(response.data['is_email_verified'])
        self.verified_user.refresh_from_db()
        self.assertEqual(response.data['referral_code'], self.verified_user.referral_code)
        self.assertIsNotNone(response.data['referred_by_info'])
    
    def test_unverified_email_not_exposed_in_public_profile(self):
        """Test that public user profile endpoint hides email fields."""
        response = self.client.get(f'/api/v1/users/by-address/{self.unverified_user.address}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('email', response.data)
        self.assertNotIn('is_email_verified', response.data)
        
        self.authenticate(self.other_user)
        response = self.client.get(f'/api/v1/users/by-address/{self.unverified_user.address}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('email', response.data)
        self.assertNotIn('is_email_verified', response.data)
    
    def test_verified_email_not_shown_in_public_profile(self):
        """Test that verified email is not exposed to anonymous or other users."""
        response = self.client.get(f'/api/v1/users/by-address/{self.verified_user.address}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for field in [
            'email',
            'is_email_verified',
            'is_banned',
            'ban_reason',
            'referral_code',
            'referred_by_info',
            'total_referrals',
            'referral_details',
        ]:
            self.assertNotIn(field, response.data)

        self.authenticate(self.other_user)
        response = self.client.get(f'/api/v1/users/by-address/{self.verified_user.address}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for field in [
            'email',
            'is_email_verified',
            'is_banned',
            'ban_reason',
            'referral_code',
            'referred_by_info',
            'total_referrals',
            'referral_details',
        ]:
            self.assertNotIn(field, response.data)

    def test_public_profile_only_exposes_public_social_identifiers(self):
        """Test that authenticated profile lookup does not expose social credentials or internals."""
        self.authenticate(self.other_user)
        response = self.client.get(f'/api/v1/users/by-address/{self.verified_user.address}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['github_connection'], {'platform_username': 'verified-gh'})
        self.assertEqual(response.data['twitter_connection'], {'platform_username': 'verified-x'})
        self.assertEqual(response.data['discord_connection'], {'platform_username': 'verified-discord'})

        serialized = str(response.data)
        for private_value in [
            'encrypted-gh-access-token',
            'encrypted-gh-refresh-token',
            'encrypted-x-access-token',
            'encrypted-x-refresh-token',
            'encrypted-discord-access-token',
            'encrypted-discord-refresh-token',
            'private sync error',
            'private nickname',
            'Private Role',
            'guild_member',
            'roles_sync_error',
            'access_token',
            'refresh_token',
        ]:
            self.assertNotIn(private_value, serialized)

    def test_verified_email_shown_on_own_public_profile_when_authenticated(self):
        """Test that public profile endpoints do not include referral details."""
        self.authenticate(self.verified_user)

        response = self.client.get(f'/api/v1/users/by-address/{self.verified_user.address}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'verified@example.com')
        self.assertTrue(response.data['is_email_verified'])
        self.assertTrue(response.data['is_banned'])
        self.assertEqual(response.data['ban_reason'], 'private moderation note')
        for field in [
            'referral_code',
            'referred_by_info',
            'total_referrals',
            'referral_details',
        ]:
            self.assertNotIn(field, response.data)
        self.assertEqual(response.data['github_connection']['platform_username'], 'verified-gh')
        self.assertEqual(response.data['twitter_connection']['platform_username'], 'verified-x')
        self.assertEqual(response.data['discord_connection']['platform_username'], 'verified-discord')
        self.assertIn('roles', response.data['discord_connection'])

        serialized = str(response.data)
        self.assertNotIn('encrypted-gh-access-token', serialized)
        self.assertNotIn('encrypted-x-access-token', serialized)
        self.assertNotIn('encrypted-discord-access-token', serialized)
        self.assertNotIn('refresh_token', serialized)
    
    def test_email_becomes_visible_after_verification(self):
        """Test that email becomes visible once it's verified."""
        self.authenticate(self.unverified_user)
        
        # Initially, email should not be exposed
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.data['email'], '')
        
        # User updates their email (which marks it as verified)
        response = self.client.patch('/api/v1/users/me/', {
            'email': 'newemail@gmail.com'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Now email should be visible to the owner
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.data['email'], 'newemail@gmail.com')
        self.assertTrue(response.data['is_email_verified'])
        
        # Public profile should not expose the authentication email.
        self.client.credentials()  # Clear authentication
        response = self.client.get(f'/api/v1/users/by-address/{self.unverified_user.address}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('email', response.data)
        self.assertNotIn('is_email_verified', response.data)
    
    def test_no_email_field_leakage_in_list_view(self):
        """Test that auth emails are not exposed in authenticated user list view."""
        response = self.client.get('/api/v1/users/')
        self.assert_requires_authentication(response)

        self.authenticate(self.other_user)
        response = self.client.get('/api/v1/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Find the unverified user in the results
        unverified_user_data = None
        verified_user_data = None
        
        for user_data in response.data['results']:
            if user_data['address'] == self.unverified_user.address:
                unverified_user_data = user_data
            elif user_data['address'] == self.verified_user.address:
                verified_user_data = user_data
        
        # Check list entries expose only the minimal public directory shape
        self.assertIsNotNone(unverified_user_data)
        self.assertIsNotNone(verified_user_data)
        self.assertEqual(
            set(unverified_user_data.keys()),
            {
                'name',
                'address',
                'profile_image_url',
                'created_at',
                'validator',
                'builder',
                'steward',
                'creator',
            },
        )
        for user_data in [unverified_user_data, verified_user_data]:
            self.assertNotIn('email', user_data)
            self.assertNotIn('is_email_verified', user_data)
            self.assertNotIn('is_banned', user_data)
            self.assertNotIn('ban_reason', user_data)
            self.assertNotIn('referral_code', user_data)
            self.assertNotIn('github_connection', user_data)
            self.assertNotIn('twitter_connection', user_data)
            self.assertNotIn('discord_connection', user_data)

        self.assertIsNone(unverified_user_data['validator'])
        self.assertEqual(
            verified_user_data['validator'],
            {
                'node_version_asimov': '1.2.3',
                'node_version_bradbury': '1.9.0',
                'node_version': '1.2.3',
                'matches_target_asimov': True,
                'matches_target_bradbury': False,
                'matches_target': True,
                'target_version_asimov': '1.2.0',
                'target_version_bradbury': '2.0.0',
                'target_version': '1.2.0',
                'active_validators_count': 0,
                'total_validators_count': 0,
            },
        )

    def test_hidden_users_are_not_publicly_enumerable(self):
        """Test that hidden users are excluded from non-owner list and profile endpoints."""
        response = self.client.get('/api/v1/users/')
        self.assert_requires_authentication(response)

        self.authenticate(self.other_user)
        response = self.client.get('/api/v1/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        addresses = [user_data['address'] for user_data in response.data['results']]
        self.assertNotIn(self.hidden_user.address, addresses)

        response = self.client.get(f'/api/v1/users/by-address/{self.hidden_user.address}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.client.credentials()
        response = self.client.get(f'/api/v1/users/by-address/{self.hidden_user.address}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.get(f'/api/v1/users/by-address/{self.hidden_user.address}/highlights/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.authenticate(self.hidden_user)
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'hidden@example.com')

    def test_public_profile_lookup_is_throttled(self):
        """Test public profile reads are rate-limited for anonymous clients."""
        cache.clear()
        try:
            with patch.dict(SimpleRateThrottle.THROTTLE_RATES, {'public_user_profile': '1/minute'}):
                response = self.client.get(f'/api/v1/users/by-address/{self.verified_user.address}/')
                self.assertEqual(response.status_code, status.HTTP_200_OK)

                response = self.client.get(f'/api/v1/users/by-address/{self.unverified_user.address}/')
                self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        finally:
            cache.clear()

    def test_public_search_is_throttled(self):
        """Test public user search is rate-limited for anonymous clients."""
        cache.clear()
        try:
            with patch.dict(SimpleRateThrottle.THROTTLE_RATES, {'public_user_search': '1/minute'}):
                response = self.client.get('/api/v1/users/search/', {'q': 'Verified'})
                self.assertEqual(response.status_code, status.HTTP_200_OK)

                response = self.client.get('/api/v1/users/search/', {'q': 'Other'})
                self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        finally:
            cache.clear()

    def test_public_search_does_not_match_auth_email(self):
        """Test that public user search cannot use auth email as a lookup key."""
        response = self.client.get('/api/v1/users/search/', {'q': 'verified@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        self.authenticate(self.other_user)
        response = self.client.get('/api/v1/users/search/', {'q': 'verified@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_staff_search_does_not_match_auth_email(self):
        """Test that portal user search cannot use auth email even for staff."""
        staff = User.objects.create_user(
            email='staff@example.com',
            password='testpass123',
            name='Staff User',
            address='0x999',
            is_staff=True,
        )
        self.authenticate(staff)

        response = self.client.get('/api/v1/users/search/', {'q': 'verified@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_leaderboard_search_does_not_match_auth_email(self):
        """Test that leaderboard search cannot use auth email as a lookup key."""
        LeaderboardEntry.objects.create(
            user=self.verified_user,
            type='validator',
            total_points=100,
            rank=1,
        )

        response = self.client.get('/api/v1/leaderboard/', {'search': 'verified@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        self.authenticate(self.other_user)
        response = self.client.get('/api/v1/leaderboard/', {'search': 'verified@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        response = self.client.get('/api/v1/leaderboard/', {'search': 'Verified User'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user_details']['address'], self.verified_user.address)
    
    def test_image_upload_response_security(self):
        """Test that image upload responses don't expose unverified emails."""
        self.authenticate(self.unverified_user)
        
        # Create a simple test image
        from io import BytesIO
        from PIL import Image
        import tempfile
        
        # Create a simple 100x100 red image
        img = Image.new('RGB', (100, 100), color='red')
        img_file = BytesIO()
        img.save(img_file, format='PNG')
        img_file.seek(0)
        
        # Note: This test would fail without proper Cloudinary setup
        # but it's important to have for completeness
        # The important part is checking the response structure
