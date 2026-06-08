from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import Category, Contribution, ContributionType, Evidence, SubmittedContribution
from leaderboard.models import GlobalLeaderboardMultiplier
from stewards.models import Steward, StewardPermission


User = get_user_model()


class StewardSubmissionSearchTest(TestCase):
    """Test steward submission search and ordering behavior."""

    def setUp(self):
        self.category = Category.objects.create(
            name='Test Category',
            slug='test',
            description='Test category',
        )
        self.contribution_type = ContributionType.objects.create(
            name='Test Type',
            slug='test-type',
            description='Test contribution type',
            category=self.category,
            min_points=0,
            max_points=100,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.contribution_type,
            multiplier_value=1,
            valid_from=timezone.now() - timezone.timedelta(days=1),
        )
        self.regular_user = User.objects.create_user(
            email='regular@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        self.steward_user = User.objects.create_user(
            email='steward@test.com',
            address='0x0987654321098765432109876543210987654321',
            password='testpass123',
        )
        self.steward = Steward.objects.create(user=self.steward_user)
        StewardPermission.objects.create(
            steward=self.steward,
            contribution_type=self.contribution_type,
            action='accept',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.steward_user)

    def _create_accepted_submission(
        self,
        *,
        points=50,
        reviewed_at=None,
        submitted_url=None,
        converted_url=None,
        title='Accepted submission',
    ) -> SubmittedContribution:
        contribution = Contribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            points=points,
            title=title,
            notes=f'{title} contribution notes',
        )
        if converted_url:
            Evidence.objects.create(
                contribution=contribution,
                url=converted_url,
                description=f'{title} converted evidence',
            )

        submission = SubmittedContribution.objects.create(
            user=self.regular_user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes=f'{title} submission notes',
            title=title,
            state='accepted',
            reviewed_by=self.steward_user,
            reviewed_at=reviewed_at or timezone.now(),
            converted_contribution=contribution,
        )
        if submitted_url:
            Evidence.objects.create(
                submitted_contribution=submission,
                url=submitted_url,
                description=f'{title} submitted evidence',
            )
        return submission

    def test_accepted_submission_search_matches_submitted_and_converted_evidence(self):
        """Accepted search covers original submitted evidence and copied contribution evidence."""
        submitted_match = self._create_accepted_submission(
            title='Submitted evidence match',
            submitted_url='https://x.com/FIREDRAGON10101/status/2060708443153928646',
        )
        converted_match = self._create_accepted_submission(
            title='Converted evidence match',
            converted_url='https://github.com/GenLayerLabs/search-demo',
        )

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'accepted',
            'include_content': 'https://x.com/FIREDRAGON10101/status/2060708443153928646',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {str(item['id']) for item in response.data['results']}
        self.assertEqual(result_ids, {str(submitted_match.id)})

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'accepted',
            'include_content': 'https://github.com/GenLayerLabs/search-demo',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {str(item['id']) for item in response.data['results']}
        self.assertEqual(result_ids, {str(converted_match.id)})

    def test_accepted_submission_search_matches_normalized_url(self):
        """Tracking params should not prevent URL searches from finding accepted evidence."""
        submission = self._create_accepted_submission(
            submitted_url='https://x.com/FIREDRAGON10101/status/2060708443153928646',
        )

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'accepted',
            'include_content': 'https://x.com/FIREDRAGON10101/status/2060708443153928646?s=20',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {str(item['id']) for item in response.data['results']}
        self.assertEqual(result_ids, {str(submission.id)})

    def test_accepted_submissions_can_order_by_points_and_reviewed_time(self):
        older_low = self._create_accepted_submission(
            points=20,
            reviewed_at=timezone.now() - timezone.timedelta(days=2),
            title='Older low points',
        )
        newer_high = self._create_accepted_submission(
            points=90,
            reviewed_at=timezone.now() - timezone.timedelta(days=1),
            title='Newer high points',
        )

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'accepted',
            'ordering': '-converted_contribution__frozen_global_points',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = [str(item['id']) for item in response.data['results']]
        self.assertEqual(result_ids[:2], [str(newer_high.id), str(older_low.id)])

        response = self.client.get('/api/v1/steward-submissions/', {
            'state': 'accepted',
            'ordering': '-reviewed_at',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = [str(item['id']) for item in response.data['results']]
        self.assertEqual(result_ids[:2], [str(newer_high.id), str(older_low.id)])
