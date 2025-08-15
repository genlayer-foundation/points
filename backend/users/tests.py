from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

User = get_user_model()


class UserProfileAPITestCase(TestCase):
    """Test cases for user profile API endpoints"""
    
    def setUp(self):
        """Set up test client and create test user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            name='Test User',
            address='0x1234567890abcdef'
        )
        self.me_url = reverse('user-me')
        
    def authenticate(self):
        """Helper method to authenticate the test client"""
        self.client.force_authenticate(user=self.user)
        
    def test_get_profile_unauthenticated(self):
        """Test that unauthenticated users cannot access profile"""
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_get_profile_authenticated(self):
        """Test getting own profile when authenticated"""
        self.authenticate()
        response = self.client.get(self.me_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Email is not included in UserSerializer
        self.assertEqual(response.data['name'], 'Test User')
        self.assertEqual(response.data['address'], '0x1234567890abcdef')
        
    def test_get_profile_includes_leaderboard_entry(self):
        """Test that profile includes leaderboard entry if exists"""
        from leaderboard.models import LeaderboardEntry
        
        LeaderboardEntry.objects.create(
            user=self.user,
            rank=5,
            total_points=100
        )
        
        self.authenticate()
        response = self.client.get(self.me_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('leaderboard_entry', response.data)
        self.assertEqual(response.data['leaderboard_entry']['rank'], 5)
        self.assertEqual(response.data['leaderboard_entry']['total_points'], 100)
        
    def test_update_profile_name_only(self):
        """Test that only name field can be updated"""
        self.authenticate()
        
        update_data = {
            'name': 'Updated Name',
            'email': 'newemail@example.com',  # Should be ignored
            'address': '0xnewaddress',  # Should be ignored
            'visible': False  # Should be ignored
        }
        
        response = self.client.patch(self.me_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh user from database
        self.user.refresh_from_db()
        
        # Check that only name was updated
        self.assertEqual(self.user.name, 'Updated Name')
        self.assertEqual(self.user.email, 'test@example.com')  # Unchanged
        self.assertEqual(self.user.address, '0x1234567890abcdef')  # Unchanged
        self.assertTrue(self.user.visible)  # Unchanged
        
    def test_update_profile_empty_name(self):
        """Test updating profile with empty name"""
        self.authenticate()
        
        response = self.client.patch(self.me_url, {'name': ''}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, '')
        
    def test_update_profile_unauthenticated(self):
        """Test that unauthenticated users cannot update profile"""
        response = self.client.patch(self.me_url, {'name': 'New Name'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_update_profile_returns_full_user_data(self):
        """Test that update returns full user data after update"""
        self.authenticate()
        
        response = self.client.patch(self.me_url, {'name': 'Updated Name'}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Name')
        # Email is not included in UserSerializer  
        self.assertEqual(response.data['address'], '0x1234567890abcdef')
        self.assertIn('id', response.data)
        self.assertIn('created_at', response.data)
        self.assertIn('updated_at', response.data)
        
    def test_update_profile_with_long_name(self):
        """Test updating profile with maximum length name"""
        self.authenticate()
        
        long_name = 'A' * 255  # Max length for name field
        response = self.client.patch(self.me_url, {'name': long_name}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, long_name)
        
    def test_update_profile_with_too_long_name(self):
        """Test that overly long names are rejected"""
        self.authenticate()
        
        too_long_name = 'A' * 256  # Exceeds max length
        response = self.client.patch(self.me_url, {'name': too_long_name}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)
        
    def test_update_profile_with_unicode_name(self):
        """Test updating profile with unicode characters in name"""
        self.authenticate()
        
        unicode_name = '日本語 한국어 Émoji 😀'
        response = self.client.patch(self.me_url, {'name': unicode_name}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, unicode_name)
        
    def test_update_profile_with_null_name(self):
        """Test that null name is handled properly"""
        self.authenticate()
        
        response = self.client.patch(
            self.me_url, 
            {'name': None}, 
            format='json'
        )
        
        # Django REST framework may return 400 for null on CharField
        # or convert to empty string depending on settings
        if response.status_code == status.HTTP_200_OK:
            self.user.refresh_from_db()
            self.assertEqual(self.user.name, '')
        else:
            # Some configurations may reject null
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_profile_endpoint_methods(self):
        """Test that only GET and PATCH methods are allowed"""
        self.authenticate()
        
        # Test allowed methods
        response = self.client.get(self.me_url)
        self.assertNotEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        response = self.client.patch(self.me_url, {'name': 'Test'}, format='json')
        self.assertNotEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Test disallowed methods
        response = self.client.post(self.me_url, {'name': 'Test'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        response = self.client.put(self.me_url, {'name': 'Test'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        response = self.client.delete(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class UserProfileSerializerTestCase(TestCase):
    """Test cases for UserProfileUpdateSerializer"""
    
    def setUp(self):
        """Set up test user"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            name='Original Name',
            address='0x1234567890abcdef'
        )
        
    def test_serializer_includes_expected_fields(self):
        """Test that serializer exposes name and node_version fields"""
        from users.serializers import UserProfileUpdateSerializer
        
        serializer = UserProfileUpdateSerializer(instance=self.user)
        
        # Should have 'name' and 'node_version' fields
        self.assertEqual(sorted(list(serializer.fields.keys())), ['name', 'node_version'])
        
    def test_serializer_validates_name_length(self):
        """Test that serializer validates name length"""
        from users.serializers import UserProfileUpdateSerializer
        
        # Valid length
        serializer = UserProfileUpdateSerializer(
            instance=self.user,
            data={'name': 'A' * 255}
        )
        self.assertTrue(serializer.is_valid())
        
        # Invalid length
        serializer = UserProfileUpdateSerializer(
            instance=self.user,
            data={'name': 'A' * 256}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)
        
    def test_serializer_ignores_other_fields(self):
        """Test that serializer ignores non-name fields"""
        from users.serializers import UserProfileUpdateSerializer
        
        serializer = UserProfileUpdateSerializer(
            instance=self.user,
            data={
                'name': 'New Name',
                'email': 'newemail@example.com',
                'address': '0xnewaddress',
                'visible': False
            },
            partial=True
        )
        
        self.assertTrue(serializer.is_valid())
        serializer.save()
        
        self.user.refresh_from_db()
        
        # Only name should be updated
        self.assertEqual(self.user.name, 'New Name')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.address, '0x1234567890abcdef')
        self.assertTrue(self.user.visible)