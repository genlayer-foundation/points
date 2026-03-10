from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import Category, Contribution, ContributionType
from leaderboard.models import GlobalLeaderboardMultiplier

User = get_user_model()


class SubmissionPermissionTests(TestCase):
    """Test role-based restrictions when creating submissions."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='builder-welcome@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        self.client.force_authenticate(user=self.user)

        self.builder_category, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={
                'name': 'Builder',
                'description': 'Builder category',
            },
        )
        self.builder_welcome_type, _ = ContributionType.objects.get_or_create(
            slug='builder-welcome',
            defaults={
                'name': 'Builder Welcome',
                'description': 'Starts the builder journey',
                'category': self.builder_category,
                'min_points': 0,
                'max_points': 20,
            },
        )
        self.builder_submission_type = ContributionType.objects.create(
            name='Deploy Contract',
            slug='test-deploy-contract',
            description='Builder contribution type',
            category=self.builder_category,
            min_points=10,
            max_points=100,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.builder_welcome_type,
            multiplier_value=1.0,
            valid_from=timezone.now() - timezone.timedelta(days=1),
            description='Test multiplier for builder welcome',
        )
        Contribution.objects.create(
            user=self.user,
            contribution_type=self.builder_welcome_type,
            points=20,
            contribution_date=timezone.now(),
            notes='Started builder journey',
        )

        self.url = reverse('submission-list')

    def test_builder_welcome_does_not_unlock_builder_submissions(self):
        """Users need full builder status, not just the welcome contribution."""
        response = self.client.post(
            self.url,
            {
                'contribution_type': self.builder_submission_type.id,
                'contribution_date': timezone.now().isoformat(),
                'notes': 'Tried to submit a builder contribution',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data['error'],
            'You must complete the Builder journey before submitting builder contributions.',
        )
