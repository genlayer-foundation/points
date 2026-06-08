from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Validator
from contributions.models import Category

User = get_user_model()


class ValidatorAPITestCase(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            name='Test User'
        )
        
        # Get or create validator category (migration may have created it)
        self.category, _ = Category.objects.get_or_create(
            slug='validator',
            defaults={
                'name': 'Validator',
                'description': 'Test validator category',
                'profile_model': 'validators.Validator'
            }
        )
        
        # Authenticate
        self.client.force_authenticate(user=self.user)
    
    def test_get_validator_profile_not_exists(self):
        """Test getting validator profile when it doesn't exist"""
        response = self.client.get('/api/v1/validators/me/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_patch_validator_profile_does_not_create_missing_profile(self):
        """PATCH /me must not create a validator profile."""
        response = self.client.patch('/api/v1/validators/me/', {
            'node_version_asimov': '1.2.3'
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Validator.objects.filter(user=self.user).exists())
        
    def test_update_validator_profile(self):
        """Test updating existing validator profile"""
        # Create profile first
        Validator.objects.create(user=self.user, node_version_asimov='1.0.0')
        
        # Update it
        response = self.client.patch('/api/v1/validators/me/', {
            'node_version_asimov': '2.0.0'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify update
        validator = Validator.objects.get(user=self.user)
        self.assertEqual(validator.node_version_asimov, '2.0.0')
    
    def test_get_validator_profile_exists(self):
        """Test getting existing validator profile"""
        Validator.objects.create(user=self.user, node_version_asimov='1.2.3')
        
        response = self.client.get('/api/v1/validators/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('node_version_asimov', response.data)
        self.assertEqual(response.data['node_version_asimov'], '1.2.3')
