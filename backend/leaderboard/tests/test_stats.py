from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from contributions.models import (
    Category,
    Contribution,
    ContributionType,
    SubmittedContribution,
)
from leaderboard.models import ReferralPoints
from users.models import User


class LeaderboardStatsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.community_category, _ = Category.objects.get_or_create(
            slug='community',
            defaults={'name': 'Community'}
        )
        self.builder_category, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={'name': 'Builder'}
        )
        self.community_type = ContributionType.objects.create(
            name='Community Post',
            slug='community-post',
            category=self.community_category
        )
        self.builder_type = ContributionType.objects.create(
            name='Builder Submission',
            slug='builder-submission',
            category=self.builder_category
        )

    def _create_user(self, email, address, visible=True):
        return User.objects.create_user(
            email=email,
            password='pass',
            address=address,
            visible=visible
        )

    def test_community_member_count_uses_accepted_community_contributions(self):
        now = timezone.now()
        community_user = self._create_user(
            'community@example.com',
            '0x0000000000000000000000000000000000000001'
        )
        repeat_community_user = self._create_user(
            'repeat@example.com',
            '0x0000000000000000000000000000000000000002'
        )
        builder_only_user = self._create_user(
            'builder@example.com',
            '0x0000000000000000000000000000000000000003'
        )
        hidden_community_user = self._create_user(
            'hidden@example.com',
            '0x0000000000000000000000000000000000000004',
            visible=False
        )
        referral_only_user = self._create_user(
            'referral@example.com',
            '0x0000000000000000000000000000000000000005'
        )
        pending_user = self._create_user(
            'pending@example.com',
            '0x0000000000000000000000000000000000000006'
        )

        Contribution.objects.bulk_create([
            Contribution(
                user=community_user,
                contribution_type=self.community_type,
                points=10,
                frozen_global_points=10,
                contribution_date=now
            ),
            Contribution(
                user=repeat_community_user,
                contribution_type=self.community_type,
                points=10,
                frozen_global_points=10,
                contribution_date=now
            ),
            Contribution(
                user=repeat_community_user,
                contribution_type=self.community_type,
                points=5,
                frozen_global_points=5,
                contribution_date=now
            ),
            Contribution(
                user=builder_only_user,
                contribution_type=self.builder_type,
                points=10,
                frozen_global_points=10,
                contribution_date=now
            ),
            Contribution(
                user=hidden_community_user,
                contribution_type=self.community_type,
                points=10,
                frozen_global_points=10,
                contribution_date=now
            ),
        ])
        ReferralPoints.objects.create(
            user=referral_only_user,
            builder_points=100,
            validator_points=100
        )
        SubmittedContribution.objects.create(
            user=pending_user,
            contribution_type=self.community_type,
            contribution_date=now,
            state='pending'
        )

        response = self.client.get('/api/v1/leaderboard/stats/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['community_member_count'], 2)
        self.assertEqual(response.data['creator_count'], 2)
