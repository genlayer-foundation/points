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
