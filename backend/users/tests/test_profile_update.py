"""Tests for user profile update functionality."""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from validators.models import Validator

from contributions.models import Category, Contribution, ContributionType
from leaderboard.models import GlobalLeaderboardMultiplier, LeaderboardEntry
from validators.models import Validator

User = get_user_model()


class UserProfileUpdateTests(TestCase):
    """Test user profile update functionality."""
    
    def setUp(self):
        """Set up test client and users."""
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
        
    def authenticate(self, user):
        """Authenticate the client with the given user."""
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_unverified_user_cannot_set_email_from_profile_patch(self):
        """Email changes must go through the verification-code flow."""
        self.authenticate(self.unverified_user)

        response = self.client.patch('/api/v1/users/me/', {
            'email': 'newemail@example.com',
            'name': 'Updated Name'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(str(response.data['email']), 'Use email verification to change email.')
        self.unverified_user.refresh_from_db()
        self.assertEqual(self.unverified_user.email, '0x123@ethereum.address')
        self.assertFalse(self.unverified_user.is_email_verified)
        self.assertEqual(self.unverified_user.name, 'Unverified User')

    def test_verified_user_cannot_change_email_from_profile_patch(self):
        """Verified users also need to confirm email changes by code."""
        self.authenticate(self.verified_user)

        response = self.client.patch('/api/v1/users/me/', {
            'email': 'changedemail@example.com'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.verified_user.refresh_from_db()
        self.assertEqual(self.verified_user.email, 'verified@example.com')
        self.assertTrue(self.verified_user.is_email_verified)

    def test_profile_patch_rejects_email_before_uniqueness_validation(self):
        """Profile save never handles email uniqueness; verification endpoints do."""
        self.authenticate(self.unverified_user)

        response = self.client.patch('/api/v1/users/me/', {
            'email': 'verified@example.com'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.unverified_user.refresh_from_db()
        self.assertEqual(self.unverified_user.email, '0x123@ethereum.address')
    
    def test_empty_email_rejected_and_profile_not_saved(self):
        """Even an empty email key must use the verification flow."""
        self.authenticate(self.verified_user)

        response = self.client.patch('/api/v1/users/me/', {
            'email': '',
            'name': 'New Name'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.verified_user.refresh_from_db()
        self.assertEqual(self.verified_user.email, 'verified@example.com')
        self.assertEqual(self.verified_user.name, 'Verified User')
    
    def test_profile_fields_update(self):
        """Test updating various profile fields."""
        self.authenticate(self.verified_user)
        
        update_data = {
            'name': 'Updated Name',
            'description': 'This is my bio',
            'website': 'https://example.com',
            'telegram_handle': 'mytelegram'
        }
        
        response = self.client.patch('/api/v1/users/me/', update_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.verified_user.refresh_from_db()
        self.assertEqual(self.verified_user.name, 'Updated Name')
        self.assertEqual(self.verified_user.description, 'This is my bio')
        self.assertEqual(self.verified_user.website, 'https://example.com')
        self.assertEqual(self.verified_user.telegram_handle, 'mytelegram')

    def test_profile_patch_does_not_create_validator_profile(self):
        """Node versions are Grafana-sourced and not writable via profile updates."""
        self.authenticate(self.verified_user)

        response = self.client.patch('/api/v1/users/me/', {
            'node_version_asimov': '1.2.3',
            'node_version_bradbury': '2.0.0',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Validator.objects.filter(user=self.verified_user).exists())
    
    def test_oauth_owned_handles_are_not_profile_editable(self):
        """Twitter and Discord handles are managed by social connections."""
        self.verified_user.twitter_handle = 'oauth_twitter'
        self.verified_user.discord_handle = 'oauth_discord'
        self.verified_user.save(update_fields=['twitter_handle', 'discord_handle'])

        self.authenticate(self.verified_user)
        
        response = self.client.patch('/api/v1/users/me/', {
            'twitter_handle': '@mytwitter',
            'discord_handle': 'mydiscord',
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.verified_user.refresh_from_db()
        self.assertEqual(self.verified_user.twitter_handle, 'oauth_twitter')
        self.assertEqual(self.verified_user.discord_handle, 'oauth_discord')
    
    def test_telegram_handle_strips_at_symbol(self):
        """Test that @ symbol is stripped from Telegram handle."""
        self.authenticate(self.verified_user)
        
        response = self.client.patch('/api/v1/users/me/', {
            'telegram_handle': '@mytelegram'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.verified_user.refresh_from_db()
        self.assertEqual(self.verified_user.telegram_handle, 'mytelegram')
    
    def test_description_length_validation(self):
        """Test that description cannot exceed 500 characters."""
        self.authenticate(self.verified_user)
        
        long_description = 'x' * 501
        response = self.client.patch('/api/v1/users/me/', {
            'description': long_description
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('description', response.data)
    
    def test_get_current_user_profile(self):
        """Test getting current user profile data."""
        self.authenticate(self.verified_user)
        
        response = self.client.get('/api/v1/users/me/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'verified@example.com')  # Should show email since verified
        self.assertTrue(response.data['is_email_verified'])
        self.assertEqual(response.data['name'], 'Verified User')
    
    def test_get_unverified_user_profile(self):
        """Test getting unverified user profile shows no email."""
        self.authenticate(self.unverified_user)
        
        response = self.client.get('/api/v1/users/me/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], '')  # Should be empty string for unverified
        self.assertFalse(response.data['is_email_verified'])
        self.assertEqual(response.data['name'], 'Unverified User')

    def test_validator_graduation_contribution_grants_profile_state(self):
        """Graduated validators are earned validators, even after a stale relation miss."""
        validator_category, _ = Category.objects.get_or_create(
            slug='validator',
            defaults={'name': 'Validator', 'description': 'Validator contributions'},
        )
        waitlist_type, _ = ContributionType.objects.update_or_create(
            slug='validator-waitlist',
            defaults={
                'name': 'Validator Waitlist',
                'category': validator_category,
                'min_points': 0,
                'max_points': 0,
            },
        )

        validator_type, _ = ContributionType.objects.update_or_create(
            slug='validator',
            defaults={
                'name': 'Validator',
                'category': validator_category,
                'min_points': 1,
                'max_points': 1,
            },
        )

        for contribution_type in [waitlist_type, validator_type]:
            GlobalLeaderboardMultiplier.objects.create(
                contribution_type=contribution_type,
                multiplier_value=1,
                valid_from=timezone.now() - timezone.timedelta(days=2),
            )

        # This used to poison the same User instance for later graduation checks.
        self.assertFalse(hasattr(self.verified_user, 'validator'))

        Contribution.objects.create(
            user=self.verified_user,
            contribution_type=waitlist_type,
            points=0,
            contribution_date=timezone.now() - timezone.timedelta(days=1),
        )
        Contribution.objects.create(
            user=self.verified_user,
            contribution_type=validator_type,
            points=1,
            contribution_date=timezone.now(),
        )

        self.assertTrue(Validator.objects.filter(user=self.verified_user).exists())
        self.assertTrue(
            LeaderboardEntry.objects.filter(user=self.verified_user, type='validator').exists()
        )
        self.assertFalse(
            LeaderboardEntry.objects.filter(user=self.verified_user, type='validator-waitlist').exists()
        )

        self.client.force_authenticate(user=self.verified_user)
        response = self.client.get('/api/v1/users/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['validator'])
        self.assertTrue(response.data['has_validator_waitlist'])
    
    def test_unauthenticated_cannot_update_profile(self):
        """Test that unauthenticated users cannot update profiles."""
        response = self.client.patch('/api/v1/users/me/', {
            'name': 'Hacker'
        })
        
        # Note: Returns 403 Forbidden instead of 401 due to permission class
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
