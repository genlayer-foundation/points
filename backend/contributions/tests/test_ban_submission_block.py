from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from contributions.models import SubmittedContribution, ContributionType, Category

User = get_user_model()


class BannedUserSubmissionBlockTest(TestCase):
    """Test that banned users cannot create new submissions."""

    def setUp(self):
        self.category = Category.objects.create(
            name='Test Category', slug='test', description='Test',
        )
        self.contribution_type = ContributionType.objects.create(
            name='Test Type', slug='test-type',
            description='Test contribution type',
            category=self.category, min_points=1, max_points=100,
        )
        self.user = User.objects.create_user(
            email='user@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        self.client = APIClient()

    def test_normal_user_can_submit(self):
        """Non-banned user can create a submission."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/submissions/', {
            'contribution_type': self.contribution_type.id,
            'contribution_date': timezone.now().date().isoformat(),
            'notes': 'My great contribution',
            'recaptcha': 'test-token',
        }, format='json')
        # Should not be 403 (may be 201 or 400 depending on recaptcha config)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_banned_user_cannot_submit(self):
        """Banned user gets 403 when trying to submit."""
        self.user.is_banned = True
        self.user.ban_reason = 'Repeated spam'
        self.user.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/submissions/', {
            'contribution_type': self.contribution_type.id,
            'contribution_date': timezone.now().date().isoformat(),
            'notes': 'Trying to submit while banned',
            'recaptcha': 'test-token',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('suspended', response.data['error'])

    def test_banned_user_error_message_mentions_appeal(self):
        """The 403 error message tells the user about the appeal option."""
        self.user.is_banned = True
        self.user.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/submissions/', {
            'contribution_type': self.contribution_type.id,
            'contribution_date': timezone.now().date().isoformat(),
            'notes': 'Test',
            'recaptcha': 'test-token',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('appeal', response.data['error'])

    def test_unbanned_user_can_submit_again(self):
        """After being unbanned, a user can submit again."""
        self.user.is_banned = True
        self.user.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/submissions/', {
            'contribution_type': self.contribution_type.id,
            'contribution_date': timezone.now().date().isoformat(),
            'notes': 'Test',
            'recaptcha': 'test-token',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Unban the user
        self.user.is_banned = False
        self.user.save()

        response = self.client.post('/api/v1/submissions/', {
            'contribution_type': self.contribution_type.id,
            'contribution_date': timezone.now().date().isoformat(),
            'notes': 'I am back with quality content',
            'recaptcha': 'test-token',
        }, format='json')
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
