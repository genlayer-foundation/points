from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from contributions.models import SubmittedContribution, ContributionType, Category
from stewards.models import Steward, StewardPermission
from datetime import datetime
from django.utils import timezone

User = get_user_model()


class StewardPermissionTest(TestCase):
    """Test steward permission system."""
    
    def setUp(self):
        """Set up test data."""
        # Create category
        self.category = Category.objects.create(
            name="Test Category",
            slug="test",
            description="Test category"
        )
        
        # Create contribution type
        self.contribution_type = ContributionType.objects.create(
            name="Test Type",
            slug="test-type",
            description="Test contribution type",
            category=self.category,
            min_points=10,
            max_points=100
        )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            email='regular@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123'
        )
        
        # Create steward user
        self.steward_user = User.objects.create_user(
            email='steward@test.com',
            address='0x0987654321098765432109876543210987654321',
            password='testpass123'
        )
        self.steward = Steward.objects.create(user=self.steward_user)

        # Grant all permissions to steward for the test contribution type
        for action in ['propose', 'accept', 'reject', 'request_more_info']:
            StewardPermission.objects.create(
                steward=self.steward,
                contribution_type=self.contribution_type,
                action=action
            )

        # Create admin user
        self.admin_user = User.objects.create_superuser(
            email='admin@test.com',
            address='0x1111111111111111111111111111111111111111',
            password='testpass123'
        )
        
        # Create a submission
        self.submission = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes="Test submission",
            state='pending'
        )
        
        self.client = APIClient()
    
    def test_non_authenticated_cannot_access_steward_endpoints(self):
        """Test that non-authenticated users cannot access steward endpoints."""
        # Try to access steward submissions list
        response = self.client.get('/api/v1/steward-submissions/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Try to review a submission
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {'action': 'accept', 'points': 50}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Try to get stats
        response = self.client.get('/api/v1/steward-submissions/stats/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_regular_user_cannot_access_steward_endpoints(self):
        """Test that regular users cannot access steward endpoints."""
        # Authenticate as regular user
        self.client.force_authenticate(user=self.regular_user)
        
        # Try to access steward submissions list
        response = self.client.get('/api/v1/steward-submissions/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Try to review a submission
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {'action': 'accept', 'points': 50}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Try to get stats
        response = self.client.get('/api/v1/steward-submissions/stats/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_steward_can_access_steward_endpoints(self):
        """Test that stewards can access steward endpoints."""
        # Authenticate as steward
        self.client.force_authenticate(user=self.steward_user)
        
        # Access steward submissions list
        response = self.client.get('/api/v1/steward-submissions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Get stats
        response = self.client.get('/api/v1/steward-submissions/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pending_count'], 1)
    
    def test_steward_can_review_submissions(self):
        """Test that stewards can review submissions."""
        # Authenticate as steward
        self.client.force_authenticate(user=self.steward_user)
        
        # Accept a submission
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 50,
                'contribution_type': self.contribution_type.id
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Reload submission
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, 'accepted')
        self.assertEqual(self.submission.reviewed_by, self.steward_user)
        self.assertIsNotNone(self.submission.converted_contribution)
        self.assertEqual(self.submission.converted_contribution.points, 50)
    
    def test_steward_can_reject_submissions(self):
        """Test that stewards can reject submissions."""
        # Authenticate as steward
        self.client.force_authenticate(user=self.steward_user)
        
        # Reject a submission
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'reject',
                'staff_reply': 'Insufficient evidence provided'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Reload submission
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, 'rejected')
        self.assertEqual(self.submission.staff_reply, 'Insufficient evidence provided')
    
    def test_steward_can_request_more_info(self):
        """Test that stewards can request more information."""
        # Authenticate as steward
        self.client.force_authenticate(user=self.steward_user)
        
        # Request more info
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'more_info',
                'staff_reply': 'Please provide URL evidence'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Reload submission
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, 'more_info_needed')
        self.assertEqual(self.submission.staff_reply, 'Please provide URL evidence')
    
    def test_steward_can_create_highlight(self):
        """Test that stewards can create highlights when accepting."""
        # Authenticate as steward
        self.client.force_authenticate(user=self.steward_user)
        
        # Accept with highlight
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 75,
                'contribution_type': self.contribution_type.id,
                'create_highlight': True,
                'highlight_title': 'Outstanding Contribution',
                'highlight_description': 'This is an exceptional contribution'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check highlight was created
        self.submission.refresh_from_db()
        self.assertTrue(self.submission.converted_contribution.highlights.exists())
        highlight = self.submission.converted_contribution.highlights.first()
        self.assertEqual(highlight.title, 'Outstanding Contribution')
    
    def test_points_validation(self):
        """Test that points are validated within contribution type limits."""
        # Authenticate as steward
        self.client.force_authenticate(user=self.steward_user)
        
        # Try to accept with points below minimum
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 5,  # Below min of 10
                'contribution_type': self.contribution_type.id
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('points', response.data)
        
        # Try to accept with points above maximum
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept',
                'points': 150,  # Above max of 100
                'contribution_type': self.contribution_type.id
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('points', response.data)
    
    def test_required_fields_validation(self):
        """Test that required fields are validated."""
        # Authenticate as steward
        self.client.force_authenticate(user=self.steward_user)
        
        # Try to accept without points
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'accept'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('points', response.data)
        
        # Try to reject without staff reply
        response = self.client.post(
            f'/api/v1/steward-submissions/{self.submission.id}/review/',
            {
                'action': 'reject'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('staff_reply', response.data)