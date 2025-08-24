from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from contributions.models import SubmittedContribution, ContributionType
from stewards.models import Steward
from datetime import date

User = get_user_model()


class StewardSubmissionPaginationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create a steward user
        self.steward = User.objects.create_user(
            email='steward@example.com',
            password='password123',
            address='0x1234567890123456789012345678901234567890'
        )
        # Create the Steward profile
        Steward.objects.create(user=self.steward)
        
        # Create a regular user for submissions
        self.user = User.objects.create_user(
            email='user@example.com',
            password='password123',
            address='0x0987654321098765432109876543210987654321'
        )
        
        # Create a contribution type
        self.contribution_type = ContributionType.objects.create(
            name='Test Contribution',
            slug='test-contribution',
            description='Test',
            min_points=10,
            max_points=100
        )
        
        # Create 37 submissions (to match the real scenario)
        for i in range(37):
            SubmittedContribution.objects.create(
                user=self.user,
                contribution_type=self.contribution_type,
                contribution_date=date.today(),
                notes=f'Test submission {i+1}',
                state='pending'
            )
        
        # Authenticate as steward
        self.client.force_authenticate(user=self.steward)
    
    def test_pagination_default_page_size(self):
        """Test that default pagination returns 10 items"""
        response = self.client.get('/api/v1/steward-submissions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['count'], 37)
        self.assertEqual(len(data['results']), 10)
        self.assertIsNotNone(data['next'])
        self.assertIsNone(data['previous'])
    
    def test_pagination_custom_page_size(self):
        """Test pagination with custom page_size parameter"""
        response = self.client.get('/api/v1/steward-submissions/?page_size=5')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['count'], 37)
        self.assertEqual(len(data['results']), 5)
        self.assertIsNotNone(data['next'])
        self.assertIsNone(data['previous'])
    
    def test_pagination_specific_page(self):
        """Test accessing specific page"""
        response = self.client.get('/api/v1/steward-submissions/?page=2&page_size=10')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['count'], 37)
        self.assertEqual(len(data['results']), 10)
        self.assertIsNotNone(data['next'])
        self.assertIsNotNone(data['previous'])
    
    def test_pagination_last_page(self):
        """Test last page with partial results"""
        response = self.client.get('/api/v1/steward-submissions/?page=4&page_size=10')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['count'], 37)
        self.assertEqual(len(data['results']), 7)  # 37 - 30 = 7 items on last page
        self.assertIsNone(data['next'])
        self.assertIsNotNone(data['previous'])
    
    def test_pagination_with_state_filter(self):
        """Test pagination works with filters"""
        # Create some accepted submissions
        for i in range(5):
            SubmittedContribution.objects.create(
                user=self.user,
                contribution_type=self.contribution_type,
                contribution_date=date.today(),
                notes=f'Accepted submission {i+1}',
                state='accepted'
            )
        
        response = self.client.get('/api/v1/steward-submissions/?state=pending&page_size=10')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['count'], 37)  # Only pending submissions
        self.assertEqual(len(data['results']), 10)
    
    def test_pagination_max_page_size(self):
        """Test that page_size is limited to max_page_size"""
        response = self.client.get('/api/v1/steward-submissions/?page_size=200')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data['count'], 37)
        # Should be limited to max_page_size (100)
        self.assertEqual(len(data['results']), 37)  # All 37 items fit within max of 100