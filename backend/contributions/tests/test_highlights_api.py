from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import Category, Contribution, ContributionHighlight, ContributionType
from leaderboard.models import GlobalLeaderboardMultiplier

User = get_user_model()


class ContributionHighlightsAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.viewer = User.objects.create_user(
            email='highlights-viewer@test.com',
            address='0x9999999999999999999999999999999999999999',
            password='testpass123',
        )
        self.client.force_authenticate(user=self.viewer)
        self.category = Category.objects.create(
            name='Highlights Test',
            slug='highlights-test',
            description='Highlights test category',
        )
        self.contribution_type = ContributionType.objects.create(
            name='Highlights Test Type',
            slug='highlights-test-type',
            description='Highlights test type',
            category=self.category,
            min_points=1,
            max_points=100,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.contribution_type,
            multiplier_value=1,
            valid_from=timezone.now() - timedelta(days=30),
        )

        for index in range(12):
            user = User.objects.create_user(
                email=f'highlight-user-{index}@test.com',
                address=f'0x{index + 1:040x}',
                password='testpass123',
            )
            contribution = Contribution.objects.create(
                user=user,
                contribution_type=self.contribution_type,
                points=10,
                contribution_date=timezone.now() - timedelta(days=index),
                title=f'Contribution {index}',
            )
            ContributionHighlight.objects.create(
                contribution=contribution,
                title=f'Highlight {index}',
                description='Highlighted contribution',
            )

    def test_highlights_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get('/api/v1/contributions/highlights/')

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_highlights_default_limit_is_kept_for_summary_views(self):
        response = self.client.get('/api/v1/contributions/highlights/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 10)

    def test_highlights_limit_zero_returns_every_highlight(self):
        response = self.client.get('/api/v1/contributions/highlights/?limit=0')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 12)

    def test_highlights_order_by_featured_date_before_contribution_date(self):
        old_contribution = Contribution.objects.create(
            user=User.objects.create_user(
                email='featured-old-contrib@test.com',
                address='0x0000000000000000000000000000000000000101',
                password='testpass123',
            ),
            contribution_type=self.contribution_type,
            points=10,
            contribution_date=timezone.now() - timedelta(days=20),
            title='Old contribution featured recently',
        )
        recent_contribution = Contribution.objects.create(
            user=User.objects.create_user(
                email='featured-recent-contrib@test.com',
                address='0x0000000000000000000000000000000000000102',
                password='testpass123',
            ),
            contribution_type=self.contribution_type,
            points=10,
            contribution_date=timezone.now(),
            title='Recent contribution featured earlier',
        )
        newer_highlight = ContributionHighlight.objects.create(
            contribution=old_contribution,
            title='Newest featured',
            description='Featured after the newer contribution',
        )
        older_highlight = ContributionHighlight.objects.create(
            contribution=recent_contribution,
            title='Older featured',
            description='Featured before the older contribution',
        )
        ContributionHighlight.objects.filter(id=newer_highlight.id).update(
            created_at=timezone.now()
        )
        ContributionHighlight.objects.filter(id=older_highlight.id).update(
            created_at=timezone.now() - timedelta(days=5)
        )

        response = self.client.get('/api/v1/contributions/highlights/?limit=0')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()[0]['title'], 'Newest featured')

    def test_highlights_rejects_negative_limit(self):
        response = self.client.get('/api/v1/contributions/highlights/?limit=-1')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
