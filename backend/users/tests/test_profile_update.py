"""
Tests for user profile update functionality, especially email updates.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

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
    
    def test_unverified_user_can_set_email(self):
        """Test that unverified users can set their email for the first time."""
        self.authenticate(self.unverified_user)
        
        # Update profile with new email
        response = self.client.patch('/api/v1/users/me/', {
            'email': 'newemail@example.com',
            'name': 'Updated Name'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh user from database
        self.unverified_user.refresh_from_db()
        
        # Check that email was updated and marked as verified
        self.assertEqual(self.unverified_user.email, 'newemail@example.com')
        self.assertTrue(self.unverified_user.is_email_verified)
        self.assertEqual(self.unverified_user.name, 'Updated Name')
    
    def test_verified_user_can_change_email(self):
        """Test that verified users can change their email."""
        self.authenticate(self.verified_user)
        
        # Update profile with new email
        response = self.client.patch('/api/v1/users/me/', {
            'email': 'changedemail@example.com'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh user from database
        self.verified_user.refresh_from_db()
        
        # Check that email was updated and still marked as verified
        self.assertEqual(self.verified_user.email, 'changedemail@example.com')
        self.assertTrue(self.verified_user.is_email_verified)
    
    def test_email_uniqueness_validation(self):
        """Test that email must be unique."""
        self.authenticate(self.unverified_user)
        
        # Try to use an email that's already taken
        response = self.client.patch('/api/v1/users/me/', {
            'email': 'verified@example.com'  # Already used by verified_user
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        
        # Check that email was not changed
        self.unverified_user.refresh_from_db()
        self.assertEqual(self.unverified_user.email, '0x123@ethereum.address')
    
    def test_empty_email_not_saved(self):
        """Test that empty email is not saved."""
        self.authenticate(self.verified_user)
        
        # Try to set empty email
        response = self.client.patch('/api/v1/users/me/', {
            'email': '',
            'name': 'New Name'
        })
        
        # Name should update but email should not change
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.verified_user.refresh_from_db()
        self.assertEqual(self.verified_user.email, 'verified@example.com')
        self.assertEqual(self.verified_user.name, 'New Name')
    
    def test_profile_fields_update(self):
        """Test updating various profile fields."""
        self.authenticate(self.verified_user)
        
        update_data = {
            'name': 'Updated Name',
            'description': 'This is my bio',
            'website': 'https://example.com',
            'twitter_handle': 'mytwitter',
            'discord_handle': 'mydiscord',
            'telegram_handle': 'mytelegram'
        }
        
        response = self.client.patch('/api/v1/users/me/', update_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check all fields were updated
        self.verified_user.refresh_from_db()
        self.assertEqual(self.verified_user.name, 'Updated Name')
        self.assertEqual(self.verified_user.description, 'This is my bio')
        self.assertEqual(self.verified_user.website, 'https://example.com')
        self.assertEqual(self.verified_user.twitter_handle, 'mytwitter')
        self.assertEqual(self.verified_user.discord_handle, 'mydiscord')
        self.assertEqual(self.verified_user.telegram_handle, 'mytelegram')
    
    def test_twitter_handle_strips_at_symbol(self):
        """Test that @ symbol is stripped from Twitter handle."""
        self.authenticate(self.verified_user)
        
        response = self.client.patch('/api/v1/users/me/', {
            'twitter_handle': '@mytwitter'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.verified_user.refresh_from_db()
        self.assertEqual(self.verified_user.twitter_handle, 'mytwitter')
    
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
    
    def test_unauthenticated_cannot_update_profile(self):
        """Test that unauthenticated users cannot update profiles."""
        response = self.client.patch('/api/v1/users/me/', {
            'name': 'Hacker'
        })
        
        # Note: Returns 403 Forbidden instead of 401 due to permission class
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)