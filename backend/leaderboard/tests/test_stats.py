from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from contributions.models import (
    Category,
    Contribution,
    ContributionType,
    Mission,
    SubmittedContribution,
)
from community_xp.models import Mee6CurrentXP, Mee6SyncRun
from creators.models import Creator
from leaderboard.models import GlobalLeaderboardMultiplier, ReferralPoints
from poaps.models import PoapClaim, PoapDrop
from social_connections.models import DiscordConnection
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
        self.community_link_x_type, _ = ContributionType.objects.get_or_create(
            slug='community-link-x',
            defaults={
                'name': 'Community Link X',
                'category': self.community_category,
                'min_points': 0,
                'max_points': 100,
            },
        )
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.community_type,
            defaults={
                'multiplier_value': 1,
                'valid_from': timezone.now() - timezone.timedelta(days=30),
            },
        )
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.builder_type,
            defaults={
                'multiplier_value': 1,
                'valid_from': timezone.now() - timezone.timedelta(days=30),
            },
        )
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=self.community_link_x_type,
            defaults={
                'multiplier_value': 1,
                'valid_from': timezone.now() - timezone.timedelta(days=30),
            },
        )

    def _create_user(self, email, address, visible=True):
        return User.objects.create_user(
            email=email,
            password='pass',
            address=address,
            visible=visible
        )

    def _create_current_mee6_xp(self, user, discord_id, xp):
        now = timezone.now()
        run = Mee6SyncRun.objects.create(
            guild_id='1237055789441487021',
            guild_name='GenLayer',
            status=Mee6SyncRun.STATUS_SUCCESS,
            page_size=1000,
            pages_fetched=1,
            players_fetched=1,
            matched_players=1,
            unmatched_players=0,
            completed_at=now,
            applied_at=now,
        )
        DiscordConnection.objects.create(
            user=user,
            platform_user_id=discord_id,
            platform_username=f'discord-{discord_id}',
            linked_at=now,
        )
        return Mee6CurrentXP.objects.create(
            guild_id=run.guild_id,
            discord_id=discord_id,
            username=f'discord-{discord_id}',
            rank=1,
            xp=xp,
            level=4,
            message_count=12,
            sync_run=run,
            matched_user=user,
            matched_at=now,
            synced_at=now,
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
        self.assertEqual(response.data['builder_count'], 1)

    def test_poap_claim_grants_role_and_counts_as_member_metric(self):
        poap_user = self._create_user(
            'poap@example.com',
            '0x0000000000000000000000000000000000000007'
        )
        drop = PoapDrop.objects.create(
            title='Community Call',
            slug='community-call',
            event_start_at=timezone.now(),
            status=PoapDrop.STATUS_ACTIVE,
        )

        PoapClaim.objects.create(
            drop=drop,
            user=poap_user,
            claim_method=PoapClaim.CLAIM_ADMIN,
        )

        response = self.client.get('/api/v1/leaderboard/stats/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['community_member_count'], 1)
        self.assertEqual(response.data['creator_count'], 1)
        self.assertTrue(Creator.objects.filter(user=poap_user).exists())

    def test_community_social_link_contributions_do_not_count_as_members_or_activity(self):
        social_user = self._create_user(
            'social@example.com',
            '0x0000000000000000000000000000000000000009'
        )
        Contribution.objects.create(
            user=social_user,
            contribution_type=self.community_link_x_type,
            points=20,
            frozen_global_points=20,
            contribution_date=timezone.now()
        )

        response = self.client.get('/api/v1/leaderboard/stats/', {'type': 'community'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['community_member_count'], 0)
        self.assertEqual(response.data['participant_count'], 0)
        self.assertEqual(response.data['contribution_count'], 0)

    def test_community_stats_use_effective_mee6_points_and_members(self):
        mee6_only_user = self._create_user(
            'mee6-only@example.com',
            '0x0000000000000000000000000000000000000010'
        )
        pending_portal_user = self._create_user(
            'pending-portal@example.com',
            '0x0000000000000000000000000000000000000011'
        )
        self._create_current_mee6_xp(mee6_only_user, 'discord-mee6-only', 100)
        Contribution.objects.create(
            user=pending_portal_user,
            contribution_type=self.community_type,
            points=80,
            frozen_global_points=80,
            contribution_date=timezone.now()
        )

        community_response = self.client.get('/api/v1/leaderboard/stats/', {'type': 'community'})
        global_response = self.client.get('/api/v1/leaderboard/stats/')

        self.assertEqual(community_response.status_code, 200)
        self.assertEqual(community_response.data['total_points'], 180)
        self.assertEqual(community_response.data['participant_count'], 2)
        self.assertEqual(community_response.data['community_member_count'], 2)
        self.assertEqual(community_response.data['creator_count'], 2)
        self.assertEqual(community_response.data['contribution_count'], 1)

        self.assertEqual(global_response.status_code, 200)
        self.assertEqual(global_response.data['total_points'], 180)
        self.assertEqual(global_response.data['participant_count'], 2)
        self.assertEqual(global_response.data['community_member_count'], 2)

    def test_recent_mee6_sync_does_not_count_existing_member_as_new(self):
        mee6_user = self._create_user(
            'existing-mee6@example.com',
            '0x0000000000000000000000000000000000000014'
        )
        self._create_current_mee6_xp(mee6_user, 'discord-existing-mee6', 100)
        creator = Creator.objects.create(user=mee6_user)
        Creator.objects.filter(pk=creator.pk).update(
            created_at=timezone.now() - timezone.timedelta(days=60)
        )

        response = self.client.get('/api/v1/leaderboard/stats/', {'type': 'community'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['community_member_count'], 1)
        self.assertEqual(response.data['new_community_members_count'], 0)

    def test_generic_community_leaderboard_uses_effective_mee6_points(self):
        mee6_user = self._create_user(
            'generic-mee6@example.com',
            '0x0000000000000000000000000000000000000012'
        )
        portal_user = self._create_user(
            'generic-portal@example.com',
            '0x0000000000000000000000000000000000000013'
        )
        self._create_current_mee6_xp(mee6_user, 'discord-generic-mee6', 100)
        Contribution.objects.create(
            user=portal_user,
            contribution_type=self.community_type,
            points=80,
            frozen_global_points=80,
            contribution_date=timezone.now()
        )

        response = self.client.get('/api/v1/leaderboard/', {'type': 'community'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['results'][0]['user_address'], mee6_user.address)
        self.assertEqual(response.data['results'][0]['total_points'], 100)
        self.assertEqual(response.data['results'][1]['user_address'], portal_user.address)
        self.assertEqual(response.data['results'][1]['total_points'], 80)

    def test_mission_backed_non_submittable_community_contribution_is_reflected(self):
        contributor = self._create_user(
            'mission-community@example.com',
            '0x0000000000000000000000000000000000000008'
        )
        mission_type = ContributionType.objects.create(
            name='Community Mission Host',
            slug='community-mission-host',
            category=self.community_category,
            min_points=1,
            max_points=100,
            is_submittable=False,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=mission_type,
            multiplier_value=1,
            valid_from=timezone.now() - timezone.timedelta(days=30),
        )
        mission = Mission.objects.create(
            name='Community Mission',
            description='Mission-backed community work',
            contribution_type=mission_type,
        )

        contribution = Contribution.objects.create(
            user=contributor,
            contribution_type=mission_type,
            mission=mission,
            points=25,
            contribution_date=timezone.now(),
        )

        stats_response = self.client.get('/api/v1/leaderboard/stats/', {'type': 'community'})
        monthly_response = self.client.get('/api/v1/leaderboard/monthly/', {'type': 'community'})

        self.assertEqual(stats_response.status_code, 200)
        self.assertEqual(stats_response.data['community_member_count'], 1)
        self.assertEqual(stats_response.data['new_community_members_count'], 1)
        self.assertEqual(stats_response.data['contribution_count'], 1)
        self.assertTrue(Creator.objects.filter(user=contributor).exists())

        self.assertEqual(monthly_response.status_code, 200)
        self.assertEqual(monthly_response.data[0]['user'], contributor.id)
        self.assertEqual(monthly_response.data[0]['total_points'], contribution.frozen_global_points)
