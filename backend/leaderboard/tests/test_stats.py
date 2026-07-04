from django.conf import settings
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
from builders.models import Builder
from community_xp.models import Mee6CurrentXP, Mee6SyncRun
from creators.models import Creator
from leaderboard.models import GlobalLeaderboardMultiplier, LeaderboardEntry, ReferralPoints
from poaps.models import PoapClaim, PoapDrop
from social_connections.models import DiscordConnection
from social_tasks.models import SocialTask, SocialTaskCompletion
from users.models import User
from validators.models import Validator


class LeaderboardStatsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.viewer = User.objects.create_user(
            email='leaderboard-viewer@example.com',
            password='pass',
            address='0xffffffffffffffffffffffffffffffffffffffff',
        )
        self.client.force_authenticate(user=self.viewer)
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
            category=self.community_category,
            max_points=10000,
        )
        self.builder_type = ContributionType.objects.create(
            name='Builder Submission',
            slug='builder-submission',
            category=self.builder_category
        )
        self.validator_category, _ = Category.objects.get_or_create(
            slug='validator',
            defaults={'name': 'Validator'}
        )
        self.validator_type = ContributionType.objects.create(
            name='Validator Uptime',
            slug='validator-uptime',
            category=self.validator_category
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
            contribution_type=self.validator_type,
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

    def _create_builder_user(self, email, address):
        user = self._create_user(email, address)
        Builder.objects.create(user=user)
        return user

    def _set_builder_entry(self, user, total_points, rank):
        LeaderboardEntry.objects.update_or_create(
            user=user,
            type='builder',
            defaults={'total_points': total_points, 'rank': rank},
        )

    def _ensure_builder_type(self, slug, name, points=0, is_submittable=False):
        contribution_type, _ = ContributionType.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'category': self.builder_category,
                'is_submittable': is_submittable,
                'min_points': points,
                'max_points': points,
            },
        )
        GlobalLeaderboardMultiplier.objects.get_or_create(
            contribution_type=contribution_type,
            defaults={
                'multiplier_value': 1,
                'valid_from': timezone.now() - timezone.timedelta(days=30),
            },
        )
        return contribution_type

    def _create_builder_contribution(self, user, contribution_type, points):
        return Contribution.objects.create(
            user=user,
            contribution_type=contribution_type,
            points=points,
            frozen_global_points=points,
            contribution_date=timezone.now(),
        )

    def _accept_builder_submission(self, user, contribution_type, points):
        contribution = self._create_builder_contribution(
            user,
            contribution_type,
            points,
        )
        SubmittedContribution.objects.create(
            user=user,
            contribution_type=contribution_type,
            contribution_date=timezone.now(),
            state='accepted',
            converted_contribution=contribution,
        )
        return contribution

    def _assert_builder_lookup_empty(self, user):
        response = self.client.get(
            '/api/v1/leaderboard/',
            {'type': 'builder', 'user_address': user.address},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def _assert_builder_list_addresses(self, response, included_users, excluded_users):
        listed_addresses = [
            row['user_details']['address']
            for row in response.data
        ]
        for user in included_users:
            self.assertIn(user.address, listed_addresses)
        for user in excluded_users:
            self.assertNotIn(user.address, listed_addresses)

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

    def test_leaderboard_allows_public_read_access(self):
        self.client.force_authenticate(user=None)

        response = self.client.get('/api/v1/leaderboard/')

        self.assertEqual(response.status_code, 200)

    def test_public_user_stats_do_not_expose_hidden_users(self):
        hidden_user = self._create_user(
            'hidden-stats@example.com',
            '0x00000000000000000000000000000000000000aa',
            visible=False,
        )
        self.client.force_authenticate(user=None)

        response = self.client.get(f'/api/v1/leaderboard/user/{hidden_user.id}/')
        self.assertEqual(response.status_code, 404)

        response = self.client.get(
            f'/api/v1/leaderboard/user_stats/by-address/{hidden_user.address}/'
        )
        self.assertEqual(response.status_code, 404)

    def test_hidden_user_can_view_own_stats(self):
        hidden_user = self._create_user(
            'own-hidden-stats@example.com',
            '0x00000000000000000000000000000000000000ab',
            visible=False,
        )
        self.client.force_authenticate(user=hidden_user)

        response = self.client.get(
            f'/api/v1/leaderboard/user_stats/by-address/{hidden_user.address}/'
        )

        self.assertEqual(response.status_code, 200)

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

    def test_poap_claim_counts_as_member_metric_without_granting_role(self):
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
        self.assertFalse(Creator.objects.filter(user=poap_user).exists())

    def test_validator_count_uses_visible_validator_table_rows(self):
        validator_user = self._create_user(
            'validator@example.com',
            '0x0000000000000000000000000000000000000012'
        )
        validator_activity_only_user = self._create_user(
            'validator-activity@example.com',
            '0x0000000000000000000000000000000000000013'
        )
        hidden_validator_user = self._create_user(
            'hidden-validator@example.com',
            '0x0000000000000000000000000000000000000014',
            visible=False
        )

        Validator.objects.create(user=validator_user)
        Validator.objects.create(user=hidden_validator_user)

        Contribution.objects.bulk_create([
            Contribution(
                user=validator_user,
                contribution_type=self.validator_type,
                points=10,
                frozen_global_points=10,
                contribution_date=timezone.now()
            ),
            Contribution(
                user=validator_activity_only_user,
                contribution_type=self.validator_type,
                points=10,
                frozen_global_points=10,
                contribution_date=timezone.now()
            ),
            Contribution(
                user=hidden_validator_user,
                contribution_type=self.validator_type,
                points=10,
                frozen_global_points=10,
                contribution_date=timezone.now()
            ),
        ])

        global_response = self.client.get('/api/v1/leaderboard/stats/')
        validator_response = self.client.get('/api/v1/leaderboard/stats/', {'type': 'validator'})

        self.assertEqual(global_response.status_code, 200)
        self.assertEqual(global_response.data['validator_count'], 1)
        self.assertEqual(global_response.data['new_validators_count'], 1)

        self.assertEqual(validator_response.status_code, 200)
        self.assertEqual(validator_response.data['validator_count'], 1)
        self.assertEqual(validator_response.data['participant_count'], 1)

    def test_community_social_link_contributions_do_not_count_as_members_or_activity(self):
        social_user = self._create_user(
            'social@example.com',
            '0x0000000000000000000000000000000000000009'
        )
        link_points = self.community_link_x_type.max_points
        Contribution.objects.create(
            user=social_user,
            contribution_type=self.community_link_x_type,
            points=link_points,
            frozen_global_points=link_points,
            contribution_date=timezone.now()
        )

        response = self.client.get('/api/v1/leaderboard/stats/', {'type': 'community'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['community_member_count'], 0)
        self.assertEqual(response.data['participant_count'], 0)
        self.assertEqual(response.data['contribution_count'], 0)
        self.assertEqual(response.data['total_points'], link_points)

    def test_builder_lookup_uses_accepted_submission_ranking_eligibility(self):
        role_only_user = self._create_builder_user(
            'builder-role-only@example.com',
            '0x0000000000000000000000000000000000000020'
        )
        non_submittable_user = self._create_builder_user(
            'builder-non-submittable@example.com',
            '0x0000000000000000000000000000000000000023'
        )
        ranked_builder = self._create_builder_user(
            'ranked-builder@example.com',
            '0x0000000000000000000000000000000000000021'
        )
        welcome_only_user = self._create_builder_user(
            'builder-welcome-only@example.com',
            '0x0000000000000000000000000000000000000025'
        )
        simple_builder_user = self._create_builder_user(
            'builder-simple-only@example.com',
            '0x0000000000000000000000000000000000000026'
        )
        github_link_user = self._create_builder_user(
            'builder-github-link-only@example.com',
            '0x0000000000000000000000000000000000000027'
        )
        contribution_only_user = self._create_builder_user(
            'builder-contribution-only@example.com',
            '0x0000000000000000000000000000000000000024'
        )
        non_submittable_type = ContributionType.objects.create(
            name='Builder Manual Review',
            slug='builder-manual-review-lookup-test',
            category=self.builder_category,
            is_submittable=False,
            min_points=50,
            max_points=50,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=non_submittable_type,
            multiplier_value=1,
            valid_from=timezone.now() - timezone.timedelta(days=30),
        )
        builder_welcome_type = self._ensure_builder_type(
            'builder-welcome',
            'Builder Welcome',
        )
        simple_builder_type = self._ensure_builder_type(
            'builder',
            'Builder',
            points=50,
        )
        github_link_type = self._ensure_builder_type(
            'community-link-github',
            'Link GitHub Account',
            points=25,
        )

        self._accept_builder_submission(
            non_submittable_user,
            non_submittable_type,
            50,
        )
        self._accept_builder_submission(ranked_builder, self.builder_type, 25)
        self._accept_builder_submission(welcome_only_user, builder_welcome_type, 0)
        self._accept_builder_submission(simple_builder_user, simple_builder_type, 50)
        self._accept_builder_submission(github_link_user, github_link_type, 25)
        self._create_builder_contribution(contribution_only_user, self.builder_type, 20)

        self._set_builder_entry(role_only_user, total_points=100, rank=1)
        self._set_builder_entry(welcome_only_user, total_points=0, rank=2)
        self._set_builder_entry(simple_builder_user, total_points=50, rank=3)
        self._set_builder_entry(non_submittable_user, total_points=50, rank=4)
        self._set_builder_entry(ranked_builder, total_points=25, rank=5)
        self._set_builder_entry(github_link_user, total_points=25, rank=6)
        self._set_builder_entry(contribution_only_user, total_points=20, rank=7)

        list_response = self.client.get('/api/v1/leaderboard/', {'type': 'builder'})
        accepted_lookup_response = self.client.get(
            '/api/v1/leaderboard/',
            {'type': 'builder', 'user_address': non_submittable_user.address},
        )
        accepted_all_entries_response = self.client.get(
            '/api/v1/leaderboard/',
            {'user_address': non_submittable_user.address},
        )
        all_entries_response = self.client.get(
            '/api/v1/leaderboard/',
            {'user_address': role_only_user.address},
        )

        self.assertEqual(list_response.status_code, 200)
        self._assert_builder_list_addresses(
            list_response,
            included_users=(ranked_builder, non_submittable_user),
            excluded_users=(
                role_only_user,
                welcome_only_user,
                simple_builder_user,
                github_link_user,
                contribution_only_user,
            ),
        )
        self.assertEqual([row['rank'] for row in list_response.data], [4, 5])

        self._assert_builder_lookup_empty(role_only_user)
        self._assert_builder_lookup_empty(welcome_only_user)
        self._assert_builder_lookup_empty(simple_builder_user)
        self._assert_builder_lookup_empty(github_link_user)

        self.assertEqual(accepted_lookup_response.status_code, 200)
        self.assertEqual(accepted_lookup_response.data[0]['type'], 'builder')
        self.assertEqual(accepted_lookup_response.data[0]['rank'], 4)

        self.assertEqual(accepted_all_entries_response.status_code, 200)
        self.assertTrue(
            any(row['type'] == 'builder' for row in accepted_all_entries_response.data)
        )

        self.assertEqual(all_entries_response.status_code, 200)
        self.assertFalse(
            any(row['type'] == 'builder' for row in all_entries_response.data)
        )

    def test_user_stats_report_submittable_contribution_count(self):
        builder_user = self._create_user(
            'builder-stats@example.com',
            '0x0000000000000000000000000000000000000022'
        )
        non_submittable_type = ContributionType.objects.create(
            name='Builder Welcome',
            slug='builder-welcome-test',
            category=self.builder_category,
            is_submittable=False,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=non_submittable_type,
            multiplier_value=1,
            valid_from=timezone.now() - timezone.timedelta(days=30),
        )

        Contribution.objects.create(
            user=builder_user,
            contribution_type=non_submittable_type,
            points=0,
            frozen_global_points=0,
            contribution_date=timezone.now(),
        )
        Contribution.objects.create(
            user=builder_user,
            contribution_type=self.builder_type,
            points=25,
            frozen_global_points=25,
            contribution_date=timezone.now(),
        )

        response = self.client.get(
            f'/api/v1/leaderboard/user_stats/by-address/{builder_user.address}/',
            {'category': 'builder'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['totalContributions'], 2)
        self.assertEqual(response.data['submittableContributionCount'], 1)

    def test_builder_user_stats_include_eligibility_excluded_contribution_points(self):
        builder_user = self._create_user(
            'builder-simple-stats@example.com',
            '0x0000000000000000000000000000000000000029'
        )
        github_link_type = self._ensure_builder_type(
            'community-link-github',
            'Link GitHub Account',
            points=25,
        )
        self._create_builder_contribution(builder_user, github_link_type, 25)
        self._create_builder_contribution(builder_user, self.builder_type, 30)

        response = self.client.get(
            f'/api/v1/leaderboard/user_stats/by-address/{builder_user.address}/',
            {'category': 'builder'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['totalPoints'], 55)
        self.assertEqual(response.data['totalContributions'], 2)
        self.assertEqual(response.data['submittableContributionCount'], 1)
        self.assertEqual(
            [row['name'] for row in response.data['contributionTypes']],
            ['Builder Submission', 'Link GitHub Account'],
        )

    def test_builder_user_stats_include_builder_journey_star_task(self):
        builder_user = self._create_user(
            'builder-social-stats@example.com',
            '0x0000000000000000000000000000000000000028'
        )
        builder_task = SocialTask.objects.create(
            slug='builder-social-stats-task',
            name='Builder social stats task',
            category=self.builder_category,
            points=7,
            verification_type='click_through',
            action_url='https://example.com',
        )
        star_task, _ = SocialTask.objects.update_or_create(
            slug=settings.BUILDER_JOURNEY_TASK_SLUG,
            defaults={
                'name': 'Star the GenLayer boilerplate',
                'category': self.builder_category,
                'points': 25,
                'verification_type': 'github_star',
                'target_repo': 'genlayerlabs/genlayer-project-boilerplate',
                'action_url': 'https://github.com/genlayerlabs/genlayer-project-boilerplate',
            },
        )
        SocialTaskCompletion.objects.create(
            user=builder_user,
            task=builder_task,
            points_awarded=7,
            verification_type='click_through',
        )
        SocialTaskCompletion.objects.create(
            user=builder_user,
            task=star_task,
            points_awarded=25,
            verification_type='github_star',
        )

        response = self.client.get(
            f'/api/v1/leaderboard/user_stats/by-address/{builder_user.address}/',
            {'category': 'builder'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['totalPoints'], 32)
        self.assertEqual(response.data['socialTaskTotal'], 32)
        self.assertEqual(response.data['socialTaskCount'], 2)

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

    def test_recent_link_only_contribution_does_not_count_as_new_community_member(self):
        link_only_user = self._create_user(
            'link-only@example.com',
            '0x0000000000000000000000000000000000000015'
        )
        Contribution.objects.create(
            user=link_only_user,
            contribution_type=self.community_link_x_type,
            points=self.community_link_x_type.max_points,
            contribution_date=timezone.now(),
        )

        response = self.client.get('/api/v1/leaderboard/stats/', {'type': 'community'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['community_member_count'], 0)
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
        self._create_current_mee6_xp(mee6_user, 'discord-generic-mee6', 5000)
        Contribution.objects.create(
            user=portal_user,
            contribution_type=self.community_type,
            points=3000,
            frozen_global_points=3000,
            contribution_date=timezone.now()
        )

        response = self.client.get('/api/v1/leaderboard/', {'type': 'community'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['results'][0]['user_address'], mee6_user.address)
        self.assertEqual(response.data['results'][0]['total_points'], 5000)
        self.assertEqual(response.data['results'][1]['user_address'], portal_user.address)
        self.assertEqual(response.data['results'][1]['total_points'], 3000)

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
        self.assertFalse(Creator.objects.filter(user=contributor).exists())

        self.assertEqual(monthly_response.status_code, 200)
        self.assertEqual(monthly_response.data[0]['user'], contributor.id)
        self.assertEqual(monthly_response.data[0]['total_points'], contribution.frozen_global_points)

    def test_monthly_leaderboard_accepts_explicit_date_range(self):
        contributor = self._create_user(
            'rolling-community@example.com',
            '0x0000000000000000000000000000000000000009'
        )
        now = timezone.localtime(timezone.now())
        previous_month_date = (
            now.replace(day=1, hour=12, minute=0, second=0, microsecond=0)
            - timezone.timedelta(days=1)
        )
        rolling_type = ContributionType.objects.create(
            name='Rolling Community Post',
            slug='rolling-community-post',
            category=self.community_category,
            min_points=1,
            max_points=100,
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=rolling_type,
            multiplier_value=1,
            valid_from=previous_month_date - timezone.timedelta(days=1),
        )

        contribution = Contribution.objects.create(
            user=contributor,
            contribution_type=rolling_type,
            points=40,
            contribution_date=previous_month_date,
        )

        default_response = self.client.get('/api/v1/leaderboard/monthly/', {'type': 'community'})
        ranged_response = self.client.get('/api/v1/leaderboard/monthly/', {
            'type': 'community',
            'start_date': previous_month_date.date().isoformat(),
            'end_date': now.date().isoformat(),
        })

        self.assertEqual(default_response.status_code, 200)
        self.assertEqual(default_response.data, [])
        self.assertEqual(ranged_response.status_code, 200)
        self.assertEqual(ranged_response.data[0]['user'], contributor.id)
        self.assertEqual(ranged_response.data[0]['total_points'], contribution.frozen_global_points)

    def test_trending_uses_top_earning_category_for_badge_and_points(self):
        contributor = self._create_user(
            'mixed-trending@example.com',
            '0x0000000000000000000000000000000000000014'
        )
        Builder.objects.create(user=contributor)
        Contribution.objects.create(
            user=contributor,
            contribution_type=self.builder_type,
            points=20,
            frozen_global_points=20,
            contribution_date=timezone.now()
        )
        Contribution.objects.create(
            user=contributor,
            contribution_type=self.community_type,
            points=55,
            frozen_global_points=55,
            contribution_date=timezone.now()
        )

        response = self.client.get('/api/v1/leaderboard/trending/', {'limit': 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['user_address'], contributor.address)
        self.assertTrue(response.data[0]['builder'])
        self.assertEqual(response.data[0]['top_category'], 'community')
        self.assertEqual(response.data[0]['top_category_points'], 55)
        self.assertEqual(response.data[0]['total_points'], 55)

    def test_trending_category_filter_only_returns_that_category_points(self):
        builder_contributor = self._create_user(
            'builder-trending@example.com',
            '0x0000000000000000000000000000000000000015'
        )
        community_contributor = self._create_user(
            'community-trending@example.com',
            '0x0000000000000000000000000000000000000016'
        )
        Contribution.objects.create(
            user=builder_contributor,
            contribution_type=self.builder_type,
            points=30,
            frozen_global_points=30,
            contribution_date=timezone.now()
        )
        Contribution.objects.create(
            user=builder_contributor,
            contribution_type=self.community_type,
            points=80,
            frozen_global_points=80,
            contribution_date=timezone.now()
        )
        Contribution.objects.create(
            user=community_contributor,
            contribution_type=self.community_type,
            points=100,
            frozen_global_points=100,
            contribution_date=timezone.now()
        )

        response = self.client.get('/api/v1/leaderboard/trending/', {
            'limit': 10,
            'category': 'builder',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user_address'], builder_contributor.address)
        self.assertEqual(response.data[0]['top_category'], 'builder')
        self.assertEqual(response.data[0]['total_points'], 30)
        self.assertEqual(response.data[0]['category_points'], {'builder': 30})
