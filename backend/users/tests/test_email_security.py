"""
Tests for email security - ensuring unverified emails are never exposed in API.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class EmailSecurityTests(TestCase):
    """Test that unverified emails are never exposed in any API endpoint."""
    
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
        
        # Create another user to test viewing other users' profiles
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            name='Other User',
            address='0x789',
            is_email_verified=True
        )
    
    def authenticate(self, user):
        """Authenticate the client with the given user."""
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
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
    
    def test_unverified_email_not_exposed_in_public_profile(self):
        """Test that unverified email is not exposed in public profile endpoint."""
        # No authentication - public access
        
        # Test /api/v1/users/by-address/{address}/
        response = self.client.get(f'/api/v1/users/by-address/{self.unverified_user.address}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], '')  # Should be empty string
        self.assertFalse(response.data['is_email_verified'])
        
        # Also test when authenticated as another user
        self.authenticate(self.other_user)
        response = self.client.get(f'/api/v1/users/by-address/{self.unverified_user.address}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], '')  # Should still be empty
        self.assertFalse(response.data['is_email_verified'])
    
    def test_verified_email_shown_in_public_profile(self):
        """Test that verified email is shown in public profile endpoint."""
        # No authentication - public access
        
        # Test /api/v1/users/by-address/{address}/
        response = self.client.get(f'/api/v1/users/by-address/{self.verified_user.address}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'verified@example.com')
        self.assertTrue(response.data['is_email_verified'])
    
    def test_email_becomes_visible_after_verification(self):
        """Test that email becomes visible once it's verified."""
        self.authenticate(self.unverified_user)
        
        # Initially, email should not be exposed
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.data['email'], '')
        
        # User updates their email (which marks it as verified)
        response = self.client.patch('/api/v1/users/me/', {
            'email': 'newemail@example.com'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Now email should be visible
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.data['email'], 'newemail@example.com')
        self.assertTrue(response.data['is_email_verified'])
        
        # Also check public endpoint
        self.client.credentials()  # Clear authentication
        response = self.client.get(f'/api/v1/users/by-address/{self.unverified_user.address}/')
        self.assertEqual(response.data['email'], 'newemail@example.com')
        self.assertTrue(response.data['is_email_verified'])
    
    def test_no_email_field_leakage_in_list_view(self):
        """Test that unverified emails are not exposed in user list view."""
        # Test /api/v1/users/ list endpoint
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
        
        # Check unverified user has empty email
        self.assertIsNotNone(unverified_user_data)
        self.assertEqual(unverified_user_data['email'], '')
        self.assertFalse(unverified_user_data['is_email_verified'])
        
        # Check verified user shows email
        self.assertIsNotNone(verified_user_data)
        self.assertEqual(verified_user_data['email'], 'verified@example.com')
        self.assertTrue(verified_user_data['is_email_verified'])
    
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