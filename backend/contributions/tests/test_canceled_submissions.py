from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import Category, Contribution, ContributionType, SubmittedContribution
from leaderboard.models import GlobalLeaderboardMultiplier
from stewards.models import Steward, StewardPermission

User = get_user_model()


class CanceledSubmissionMetricsTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Test', slug='test', description='Test',
        )
        self.contribution_type = ContributionType.objects.create(
            name='Test Type',
            slug='test-type',
            description='Test type',
            category=self.category,
            min_points=1,
            max_points=10,
        )
        self.user = User.objects.create_user(
            email='user@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        self.steward = Steward.objects.create(user=self.user)
        self._grant_permissions(self.contribution_type)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _grant_permissions(self, contribution_type):
        for action in ['propose', 'accept', 'reject', 'request_more_info']:
            StewardPermission.objects.get_or_create(
                steward=self.steward,
                contribution_type=contribution_type,
                action=action,
            )

    def _category(self, name, slug, description):
        existing = Category.objects.filter(slug=slug).first() or Category.objects.filter(name=name).first()
        if existing:
            return existing
        return Category.objects.create(name=name, slug=slug, description=description)

    def _contribution_type(self, name, slug, description, category):
        existing = ContributionType.objects.filter(slug=slug).first()
        if existing:
            return existing
        return ContributionType.objects.create(
            name=name,
            slug=slug,
            description=description,
            category=category,
            min_points=0,
            max_points=1000,
        )

    def _create_submission(self, state, staff_reply=''):
        return SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=self.contribution_type,
            contribution_date=timezone.now(),
            notes='Test submission',
            state=state,
            staff_reply=staff_reply,
            reviewed_by=self.user,
            reviewed_at=timezone.now(),
        )

    def test_canceled_submissions_are_not_counted_as_rejected(self):
        self._create_submission(state='rejected', staff_reply='Not valid')
        self._create_submission(state='canceled', staff_reply='Canceled by user')

        today = timezone.now().date().isoformat()
        response = self.client.get(
            '/api/v1/steward-submissions/daily-metrics/',
            {
                'group_by': 'day',
                'start_date': today,
                'end_date': today,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['totals']['rejected'], 1)
        self.assertEqual(response.data['totals']['canceled'], 1)

    def test_daily_metrics_are_public_aggregate_counts(self):
        self._create_submission(state='accepted', staff_reply='Accepted')
        self.client.force_authenticate(user=None)

        today = timezone.now().date().isoformat()
        response = self.client.get(
            '/api/v1/steward-submissions/daily-metrics/',
            {
                'group_by': 'day',
                'start_date': today,
                'end_date': today,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['totals']['accepted'], 1)

    def test_daily_metrics_state_totals_reflect_state_not_submission_date(self):
        old = timezone.now() - timedelta(days=10)

        old_pending = self._create_submission(state='pending')
        SubmittedContribution.objects.filter(pk=old_pending.pk).update(
            created_at=old, reviewed_at=None, reviewed_by=None,
        )
        old_accepted = self._create_submission(state='accepted', staff_reply='Accepted')
        SubmittedContribution.objects.filter(pk=old_accepted.pk).update(
            created_at=old, reviewed_at=old,
        )

        today = timezone.now().date().isoformat()
        response = self.client.get(
            '/api/v1/steward-submissions/daily-metrics/',
            {
                'group_by': 'day',
                'start_date': today,
                'end_date': today,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Nothing was submitted or reviewed inside the range itself...
        self.assertEqual(response.data['totals']['ingress'], 0)
        self.assertEqual(response.data['totals']['accepted'], 0)
        # ...but the state series reflects what was in each state during it.
        self.assertEqual(response.data['totals']['pending_review'], 1)
        point = response.data['data'][-1]
        self.assertEqual(point['pending_total'], 1)
        self.assertEqual(point['accepted_total'], 1)
        self.assertEqual(point['more_info_total'], 0)

    def test_daily_metrics_rejects_inverted_date_range(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            '/api/v1/steward-submissions/daily-metrics/',
            {
                'group_by': 'day',
                'start_date': '2026-02-01',
                'end_date': '2026-01-01',
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'start_date must be before or equal to end_date.')

    def test_daily_metrics_rejects_too_large_public_date_range(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            '/api/v1/steward-submissions/daily-metrics/',
            {
                'group_by': 'day',
                'start_date': '2020-01-01',
                'end_date': '2022-01-01',
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'Date range is too large for group_by=day.')

    def test_steward_stats_are_public_aggregate_counts_for_anonymous_users(self):
        self._create_submission(state='pending')
        self._create_submission(state='accepted', staff_reply='Accepted')
        self._create_submission(state='rejected', staff_reply='Rejected')
        self._create_submission(state='canceled', staff_reply='Canceled by user')
        self.client.force_authenticate(user=None)

        response = self.client.get('/api/v1/steward-submissions/stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pending_count'], 1)
        self.assertEqual(response.data['total_reviewed'], 2)
        self.assertEqual(response.data['total_accepted'], 1)
        self.assertEqual(response.data['total_rejected'], 1)
        self.assertEqual(response.data['acceptance_rate'], 50.0)

    def test_canceled_submissions_are_not_reviewed_decisions(self):
        self._create_submission(state='rejected', staff_reply='Not valid')
        self._create_submission(state='canceled', staff_reply='Canceled by user')

        response = self.client.get('/api/v1/steward-submissions/stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_reviewed'], 1)
        self.assertEqual(response.data['total_rejected'], 1)

    def test_daily_metrics_points_exclude_onboarding_and_social_linking_awards(self):
        builder_category = self._category(
            name='Builder', slug='builder', description='Builder',
        )
        community_category = self._category(
            name='Community', slug='community', description='Community',
        )
        real_type = ContributionType.objects.create(
            name='Real Contribution',
            slug='metrics-real-contribution',
            description='Real contribution',
            category=builder_category,
            min_points=0,
            max_points=1000,
        )
        excluded_types = [
            self._contribution_type(
                name='Builder Welcome',
                slug='builder-welcome',
                description='Builder welcome',
                category=builder_category,
            ),
            self._contribution_type(
                name='Builder',
                slug='builder',
                description='Builder social linking',
                category=builder_category,
            ),
            self._contribution_type(
                name='Link X Account',
                slug='community-link-x',
                description='Community X link',
                category=community_category,
            ),
            self._contribution_type(
                name='Link Discord Account',
                slug='community-link-discord',
                description='Community Discord link',
                category=community_category,
            ),
        ]
        for contribution_type in [real_type, *excluded_types]:
            self._grant_permissions(contribution_type)
            GlobalLeaderboardMultiplier.objects.create(
                contribution_type=contribution_type,
                multiplier_value=1.0,
                valid_from=timezone.now() - timedelta(days=1),
            )

        today = timezone.now()
        real_submission = SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=real_type,
            contribution_date=today,
            notes='Real submission',
            state='accepted',
            reviewed_by=self.user,
            reviewed_at=today,
        )
        real_contribution = Contribution.objects.create(
            user=self.user,
            contribution_type=real_type,
            points=100,
            frozen_global_points=100,
            contribution_date=today,
            notes='Real contribution',
        )
        real_submission.converted_contribution = real_contribution
        real_submission.save(update_fields=['converted_contribution'])

        for contribution_type in excluded_types:
            points = contribution_type.min_points
            submission = SubmittedContribution.objects.create(
                user=self.user,
                contribution_type=contribution_type,
                contribution_date=today,
                notes='Excluded submission',
                state='accepted',
                reviewed_by=self.user,
                reviewed_at=today,
            )
            contribution = Contribution.objects.create(
                user=self.user,
                contribution_type=contribution_type,
                points=points,
                frozen_global_points=points,
                contribution_date=today,
                notes='Excluded contribution',
            )
            submission.converted_contribution = contribution
            submission.save(update_fields=['converted_contribution'])

        response = self.client.get(
            '/api/v1/steward-submissions/daily-metrics/',
            {
                'group_by': 'day',
                'start_date': today.date().isoformat(),
                'end_date': today.date().isoformat(),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['totals']['accepted'], 5)
        self.assertEqual(response.data['totals']['points_awarded'], 100)
