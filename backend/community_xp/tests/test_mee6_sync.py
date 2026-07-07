from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.admin.sites import AdminSite
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from community_xp.admin import Mee6SyncRunAdmin
from community_xp.models import (
    Mee6CurrentXP,
    Mee6PlayerSnapshot,
    Mee6SyncRun,
)
from community_xp.services import (
    Mee6FetchResult,
    Mee6SyncError,
    NormalizedMee6Player,
    apply_sync_run,
    run_mee6_sync,
)
from community_xp.utils import get_effective_community_points
from contributions.models import Category, Contribution, ContributionDiscordXPState, ContributionType
from creators.models import Creator
from leaderboard.models import GlobalLeaderboardMultiplier
from social_connections.serializers import DiscordConnectionSerializer
from social_connections.models import DiscordConnection
from users.models import User


class FakeMee6Client:
    def __init__(self, players=None, error=None, pages_fetched=1, duplicate_players=0):
        self.players = players or []
        self.error = error
        self.pages_fetched = pages_fetched
        self.duplicate_players = duplicate_players

    def fetch_all_players(self, guild_id, page_size):
        if self.error:
            raise self.error
        return Mee6FetchResult(
            guild_id=str(guild_id),
            guild_name='GenLayer',
            page_size=page_size,
            pages_fetched=self.pages_fetched,
            players=self.players,
            duplicate_players=self.duplicate_players,
        )


def mee6_player(discord_id, xp, rank=1, username='discord-user'):
    return NormalizedMee6Player(
        discord_id=str(discord_id),
        username=username,
        discriminator='0',
        avatar_hash='avatar',
        rank=rank,
        xp=xp,
        level=1,
        message_count=10,
        detailed_xp=[0, 100, xp],
        raw_player={
            'id': str(discord_id),
            'username': username,
            'xp': xp,
            'level': 1,
            'message_count': 10,
            'detailed_xp': [0, 100, xp],
        },
    )


@override_settings(DISCORD_GUILD_ID='guild-1')
class Mee6SyncTest(TestCase):
    def setUp(self):
        self.api_client = APIClient()
        self.community_category, _ = Category.objects.get_or_create(
            slug='community',
            defaults={
                'name': 'Community',
                'description': 'Community',
                'profile_model': '',
            },
        )
        self.community_type = ContributionType.objects.create(
            name='Special Quest',
            slug='community-special-quest-test',
            category=self.community_category,
            min_points=0,
            max_points=1_000_000,
            is_submittable=True,
        )
        self.discord_link_type, _ = ContributionType.objects.update_or_create(
            slug='community-link-discord',
            defaults={
                'name': 'Link Discord Account',
                'category': self.community_category,
                'min_points': 20,
                'max_points': 20,
                'is_submittable': False,
            },
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.community_type,
            multiplier_value=1,
            valid_from=timezone.now() - timedelta(days=30),
            description='Test multiplier',
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=self.discord_link_type,
            multiplier_value=1,
            valid_from=timezone.now() - timedelta(days=30),
            description='Test link multiplier',
        )
        self.user = User.objects.create_user(
            email='user@example.com',
            password='pass',
            address='0x0000000000000000000000000000000000000001',
            name='User One',
        )
        self.api_client.force_authenticate(user=self.user)
        self.request_factory = RequestFactory()

    def add_community_contribution(self, user, points):
        return Contribution.objects.create(
            user=user,
            contribution_type=self.community_type,
            points=points,
            contribution_date=timezone.now(),
            notes='Community audit row',
        )

    def add_discord_link_contribution(self, user):
        return Contribution.objects.create(
            user=user,
            contribution_type=self.discord_link_type,
            points=20,
            contribution_date=timezone.now(),
            notes='Discord link audit row',
        )

    def mark_discord_xp_distributed(self, contribution):
        state = contribution.discord_xp_state
        state.awarded_amount = int(contribution.frozen_global_points or 0)
        state.status = ContributionDiscordXPState.STATUS_DISTRIBUTED
        state.distributed_at = timezone.now()
        state.save(update_fields=['awarded_amount', 'status', 'distributed_at', 'updated_at'])
        return state

    def link_discord(self, user, discord_id='discord-1'):
        return DiscordConnection.objects.create(
            user=user,
            platform_user_id=discord_id,
            platform_username=f'user-{discord_id}',
            linked_at=timezone.now(),
        )

    def fetch_mee6_run(self, players):
        result = run_mee6_sync(
            client=FakeMee6Client(players=players),
            use_lock=False,
        )
        return Mee6SyncRun.objects.get(pk=result['run_id'])

    def fetch_and_apply_mee6_run(self, players):
        run = self.fetch_mee6_run(players)
        apply_sync_run(run)
        run.refresh_from_db()
        return run

    def test_admin_action_fetches_new_snapshot_from_selected_run_settings(self):
        source_run = Mee6SyncRun.objects.create(
            guild_id='guild-2',
            page_size=500,
            status=Mee6SyncRun.STATUS_SUCCESS,
        )
        request = Mock(user=self.user)
        model_admin = Mee6SyncRunAdmin(Mee6SyncRun, AdminSite())
        model_admin.has_add_permission = Mock(return_value=True)
        model_admin.has_change_permission = Mock(return_value=True)
        model_admin.message_user = Mock()

        with patch('community_xp.admin.run_mee6_sync') as run_mee6_sync_mock:
            run_mee6_sync_mock.return_value = {
                'run_id': 123,
                'players_fetched': 10,
                'matched_players': 7,
                'unmatched_players': 3,
                'pages_fetched': 1,
            }
            model_admin.fetch_new_snapshot(
                request,
                Mee6SyncRun.objects.filter(pk=source_run.pk),
            )

        run_mee6_sync_mock.assert_called_once_with(
            guild_id='guild-2',
            page_size=500,
        )
        self.assertIn('Fetched MEE6 sync #123', model_admin.message_user.call_args.args[1])

    def test_admin_fetch_button_fetches_new_snapshot_with_default_settings(self):
        request = self.request_factory.post('/admin/community_xp/mee6syncrun/fetch-new-snapshot/')
        request.user = self.user
        model_admin = Mee6SyncRunAdmin(Mee6SyncRun, AdminSite())
        model_admin.has_add_permission = Mock(return_value=True)
        model_admin.message_user = Mock()

        with patch('community_xp.admin.run_mee6_sync') as run_mee6_sync_mock:
            run_mee6_sync_mock.return_value = {
                'run_id': 124,
                'players_fetched': 11,
                'matched_players': 8,
                'unmatched_players': 3,
                'pages_fetched': 2,
            }
            response = model_admin.fetch_new_snapshot_view(request)

        run_mee6_sync_mock.assert_called_once_with(
            guild_id=None,
            page_size=None,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('Fetched MEE6 sync #124', model_admin.message_user.call_args.args[1])

    def test_admin_fetch_button_requires_add_permission(self):
        request = self.request_factory.post('/admin/community_xp/mee6syncrun/fetch-new-snapshot/')
        request.user = self.user
        model_admin = Mee6SyncRunAdmin(Mee6SyncRun, AdminSite())
        model_admin.has_add_permission = Mock(return_value=False)

        with patch('community_xp.admin.run_mee6_sync') as run_mee6_sync_mock:
            with self.assertRaises(PermissionDenied):
                model_admin.fetch_new_snapshot_view(request)

        run_mee6_sync_mock.assert_not_called()

    def test_admin_selected_run_fetch_requires_add_and_change_permission(self):
        source_run = Mee6SyncRun.objects.create(
            guild_id='guild-2',
            page_size=500,
            status=Mee6SyncRun.STATUS_SUCCESS,
        )
        request = Mock(user=self.user)
        model_admin = Mee6SyncRunAdmin(Mee6SyncRun, AdminSite())
        model_admin.has_add_permission = Mock(return_value=True)
        model_admin.has_change_permission = Mock(return_value=False)

        with patch('community_xp.admin.run_mee6_sync') as run_mee6_sync_mock:
            with self.assertRaises(PermissionDenied):
                model_admin.fetch_new_snapshot(
                    request,
                    Mee6SyncRun.objects.filter(pk=source_run.pk),
                )

        run_mee6_sync_mock.assert_not_called()

    def test_pre_sync_uses_all_portal_community_points(self):
        self.add_community_contribution(self.user, 40)

        breakdown = get_effective_community_points(self.user)

        self.assertEqual(breakdown['total_points'], 40)
        self.assertEqual(breakdown['tracked_portal_points_all_time'], 40)
        self.assertEqual(breakdown['pending_portal_points'], 40)
        self.assertEqual(breakdown['discord_xp'], 0)
        self.assertFalse(breakdown['has_discord_xp_snapshot'])

    def test_onboarding_link_rewards_are_auditable_and_count_as_points(self):
        link_contribution = self.add_discord_link_contribution(self.user)
        self.add_community_contribution(self.user, 40)

        breakdown = get_effective_community_points(self.user)

        self.assertTrue(ContributionDiscordXPState.objects.filter(contribution=link_contribution).exists())
        self.assertEqual(Contribution.objects.count(), 2)
        self.assertEqual(breakdown['total_points'], 60)
        self.assertEqual(breakdown['tracked_portal_points_all_time'], 60)
        self.assertEqual(breakdown['pending_portal_points'], 60)
        self.assertEqual(breakdown['community_contribution_count'], 2)

    def test_pending_onboarding_link_reward_does_not_block_baseline_apply(self):
        self.link_discord(self.user)
        link_contribution = self.add_discord_link_contribution(self.user)

        run = self.fetch_mee6_run([mee6_player('discord-1', 100)])
        apply_sync_run(run)
        post_baseline_link_contribution = self.add_discord_link_contribution(self.user)
        breakdown = get_effective_community_points(self.user)

        link_contribution.discord_xp_state.refresh_from_db()
        post_baseline_link_contribution.discord_xp_state.refresh_from_db()
        self.assertEqual(link_contribution.discord_xp_state.status, ContributionDiscordXPState.STATUS_PENDING)
        self.assertEqual(post_baseline_link_contribution.discord_xp_state.status, ContributionDiscordXPState.STATUS_PENDING)
        self.assertEqual(breakdown['discord_xp'], 100)
        self.assertEqual(breakdown['pending_portal_points'], 40)
        self.assertEqual(breakdown['tracked_portal_points_all_time'], 40)
        self.assertEqual(breakdown['total_points'], 140)

    def test_sync_preserves_contributions_and_counts_mee6_plus_pending_portal_points(self):
        self.link_discord(self.user)
        old_contribution = self.add_community_contribution(self.user, 40)
        before = list(Contribution.objects.values('id', 'points', 'frozen_global_points', 'notes'))

        run = self.fetch_mee6_run([mee6_player('discord-1', 100)])
        pre_apply_breakdown = get_effective_community_points(self.user)
        self.assertEqual(pre_apply_breakdown['total_points'], 40)
        self.assertFalse(Mee6CurrentXP.objects.filter(discord_id='discord-1').exists())

        apply_sync_run(run)
        run.refresh_from_db()
        post_contribution = self.add_community_contribution(self.user, 10)

        after_existing = list(
            Contribution.objects
            .filter(id__in=[old_contribution.id])
            .values('id', 'points', 'frozen_global_points', 'notes')
        )
        breakdown = get_effective_community_points(self.user)

        self.assertEqual(before, after_existing)
        self.assertEqual(Contribution.objects.count(), 2)
        self.assertEqual(old_contribution.points, 40)
        self.assertEqual(post_contribution.points, 10)
        self.assertEqual(run.status, Mee6SyncRun.STATUS_SUCCESS)
        self.assertIsNotNone(run.applied_at)
        self.assertEqual(breakdown['discord_xp'], 100)
        self.assertEqual(breakdown['pending_portal_points'], 50)
        self.assertEqual(breakdown['tracked_portal_points_all_time'], 50)
        self.assertEqual(breakdown['total_points'], 150)
        self.assertFalse(Creator.objects.filter(user=self.user).exists())

    def test_post_baseline_distributed_points_count_until_next_mee6_baseline(self):
        self.link_discord(self.user)
        first_contribution = self.add_community_contribution(self.user, 40)
        self.mark_discord_xp_distributed(first_contribution)

        self.fetch_and_apply_mee6_run([mee6_player('discord-1', 100)])
        second_contribution = self.add_community_contribution(self.user, 10)

        first_breakdown = get_effective_community_points(self.user)
        self.assertEqual(first_breakdown['total_points'], 110)
        self.assertEqual(first_breakdown['pending_portal_points'], 10)

        self.mark_discord_xp_distributed(second_contribution)
        distributed_not_yet_synced = get_effective_community_points(self.user)
        self.assertEqual(distributed_not_yet_synced['total_points'], 110)
        self.assertEqual(distributed_not_yet_synced['pending_portal_points'], 10)

        second_run = self.fetch_mee6_run([mee6_player('discord-1', 150)])
        fetched_but_not_applied = get_effective_community_points(self.user)
        self.assertEqual(fetched_but_not_applied['discord_xp'], 100)
        self.assertEqual(fetched_but_not_applied['total_points'], 110)

        apply_sync_run(second_run)
        second_breakdown = get_effective_community_points(self.user)

        self.assertEqual(second_breakdown['discord_xp'], 150)
        self.assertEqual(second_breakdown['pending_portal_points'], 0)
        self.assertEqual(second_breakdown['tracked_portal_points_all_time'], 50)
        self.assertEqual(second_breakdown['total_points'], 150)
        self.assertEqual(Contribution.objects.count(), 2)

    def test_unmatched_snapshot_is_stored_without_creating_user(self):
        user_count = User.objects.count()
        run = self.fetch_mee6_run([mee6_player('unmatched-discord', 77)])

        snapshot = Mee6PlayerSnapshot.objects.get(discord_id='unmatched-discord')
        self.assertEqual(snapshot.xp, 77)
        self.assertFalse(Mee6CurrentXP.objects.filter(discord_id='unmatched-discord').exists())

        apply_sync_run(run)
        current = Mee6CurrentXP.objects.get(discord_id='unmatched-discord')

        self.assertIsNone(current.matched_user)
        self.assertEqual(User.objects.count(), user_count)

    def test_late_discord_link_matches_current_xp_without_creating_creator_profile(self):
        run = self.fetch_mee6_run([mee6_player('late-discord', 77)])
        late_user = User.objects.create_user(
            email='late@example.com',
            password='pass',
            address='0x0000000000000000000000000000000000000002',
            name='Late User',
        )

        self.link_discord(late_user, discord_id='late-discord')
        self.assertFalse(Mee6CurrentXP.objects.filter(discord_id='late-discord').exists())

        apply_sync_run(run)
        current = Mee6CurrentXP.objects.get(discord_id='late-discord')
        breakdown = get_effective_community_points(late_user)

        self.assertEqual(current.matched_user, late_user)
        self.assertFalse(Creator.objects.filter(user=late_user).exists())
        self.assertEqual(breakdown['discord_xp'], 77)
        self.assertEqual(breakdown['total_points'], 77)

    def test_zero_xp_migration_does_not_create_creator_profile(self):
        self.link_discord(self.user, discord_id='zero-discord')

        self.fetch_and_apply_mee6_run([mee6_player('zero-discord', 0)])

        self.assertFalse(Creator.objects.filter(user=self.user).exists())

    def test_discord_connection_serializer_exposes_mee6_level_and_rank(self):
        connection = self.link_discord(self.user, discord_id='discord-1')
        self.fetch_and_apply_mee6_run([mee6_player('discord-1', 100, rank=7)])

        data = DiscordConnectionSerializer(connection).data

        self.assertEqual(data['mee6_xp'], 100)
        self.assertEqual(data['mee6_level'], 1)
        self.assertEqual(data['mee6_rank'], 7)
        self.assertIsNotNone(data['mee6_synced_at'])

    def test_failed_run_does_not_apply_current_xp(self):
        self.link_discord(self.user)
        self.fetch_and_apply_mee6_run([mee6_player('discord-1', 100)])

        with self.assertRaises(Mee6SyncError):
            run_mee6_sync(
                client=FakeMee6Client(error=Mee6SyncError('MEE6 unavailable')),
                use_lock=False,
            )

        current = Mee6CurrentXP.objects.get(discord_id='discord-1')
        self.assertEqual(current.xp, 100)
        self.assertTrue(Mee6SyncRun.objects.filter(status=Mee6SyncRun.STATUS_FAILED).exists())

    def test_disappearing_user_loses_mee6_baseline_on_next_successful_sync(self):
        self.link_discord(self.user)
        self.fetch_and_apply_mee6_run([mee6_player('discord-1', 100)])

        second_run = self.fetch_mee6_run([mee6_player('other-discord', 5)])
        fetched_but_not_applied = get_effective_community_points(self.user)
        self.assertTrue(Mee6CurrentXP.objects.filter(discord_id='discord-1').exists())
        self.assertEqual(fetched_but_not_applied['discord_xp'], 100)

        apply_sync_run(second_run)
        breakdown = get_effective_community_points(self.user)

        self.assertFalse(Mee6CurrentXP.objects.filter(discord_id='discord-1').exists())
        self.assertEqual(breakdown['discord_xp'], 0)
        self.assertEqual(breakdown['total_points'], 0)

    def test_discord_relink_uses_current_connection_and_clears_old_cached_match(self):
        connection = self.link_discord(self.user, discord_id='old-discord')
        self.fetch_and_apply_mee6_run([
            mee6_player('old-discord', 100, rank=1),
            mee6_player('new-discord', 200, rank=2),
        ])

        connection.platform_user_id = 'new-discord'
        connection.platform_username = 'new-user'
        connection.save(update_fields=['platform_user_id', 'platform_username'])

        old_current = Mee6CurrentXP.objects.get(discord_id='old-discord')
        new_current = Mee6CurrentXP.objects.get(discord_id='new-discord')
        breakdown = get_effective_community_points(self.user)

        self.assertIsNone(old_current.matched_user)
        self.assertEqual(new_current.matched_user, self.user)
        self.assertEqual(breakdown['discord_xp'], 200)
        self.assertEqual(breakdown['total_points'], 200)

    def test_discord_role_sync_save_does_not_rewrite_current_xp_match(self):
        connection = self.link_discord(self.user, discord_id='discord-1')
        self.fetch_and_apply_mee6_run([mee6_player('discord-1', 100)])
        current = Mee6CurrentXP.objects.get(discord_id='discord-1')
        original_matched_at = current.matched_at
        original_updated_at = current.updated_at

        connection.guild_checked_at = timezone.now()
        connection.save(update_fields=['guild_checked_at'])

        current.refresh_from_db()
        self.assertEqual(current.matched_user, self.user)
        self.assertEqual(current.matched_at, original_matched_at)
        self.assertEqual(current.updated_at, original_updated_at)

    def test_invalid_page_size_raises_sync_error_without_creating_run(self):
        run_count = Mee6SyncRun.objects.count()

        with self.assertRaises(Mee6SyncError):
            run_mee6_sync(page_size='not-a-number', client=FakeMee6Client(), use_lock=False)

        self.assertEqual(Mee6SyncRun.objects.count(), run_count)

    def test_community_contributors_uses_effective_points(self):
        self.link_discord(self.user)
        other = User.objects.create_user(
            email='other@example.com',
            password='pass',
            address='0x0000000000000000000000000000000000000003',
            name='Other User',
        )

        self.fetch_and_apply_mee6_run([mee6_player('discord-1', 5000)])
        self.add_community_contribution(other, 3000)

        response = self.api_client.get('/api/v1/leaderboard/community-contributors/')

        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        # Public payloads carry truncated addresses (users.utils).
        from users.utils import truncate_address
        self.assertEqual(results[0]['user_address'], truncate_address(self.user.address))
        self.assertEqual(results[0]['total_points'], 5000)
        self.assertEqual(results[0]['discord_xp'], 5000)
        self.assertEqual(results[1]['user_address'], truncate_address(other.address))
        self.assertEqual(results[1]['total_points'], 3000)
        self.assertEqual(results[1]['pending_portal_points'], 3000)

    def test_pending_pre_snapshot_contribution_counts_on_top_of_mee6_baseline(self):
        self.link_discord(self.user, discord_id='discord-1')
        self.add_community_contribution(self.user, 25)

        run = self.fetch_mee6_run([mee6_player('discord-1', 100)])
        apply_sync_run(run)

        breakdown = get_effective_community_points(self.user)

        self.assertTrue(Mee6CurrentXP.objects.filter(discord_id='discord-1').exists())
        self.assertEqual(breakdown['discord_xp'], 100)
        self.assertEqual(breakdown['pending_portal_points'], 25)
        self.assertEqual(breakdown['total_points'], 125)

    def test_cannot_apply_mee6_snapshot_when_contribution_was_distributed_after_snapshot(self):
        self.link_discord(self.user, discord_id='discord-1')
        contribution = self.add_community_contribution(self.user, 25)
        stale_run = self.fetch_mee6_run([mee6_player('discord-1', 100)])
        self.mark_discord_xp_distributed(contribution)

        with self.assertRaisesRegex(Mee6SyncError, 'marked distributed after this snapshot'):
            apply_sync_run(stale_run)

        self.assertFalse(Mee6CurrentXP.objects.filter(discord_id='discord-1').exists())

    def test_cannot_apply_mee6_snapshot_when_newer_contribution_was_distributed_after_snapshot(self):
        self.link_discord(self.user, discord_id='discord-1')
        stale_run = self.fetch_mee6_run([mee6_player('discord-1', 100)])
        contribution = self.add_community_contribution(self.user, 25)
        self.mark_discord_xp_distributed(contribution)

        with self.assertRaisesRegex(Mee6SyncError, 'marked distributed after this snapshot'):
            apply_sync_run(stale_run)

        self.assertFalse(Mee6CurrentXP.objects.filter(discord_id='discord-1').exists())

    def test_cannot_apply_older_mee6_snapshot_after_newer_baseline(self):
        self.link_discord(self.user, discord_id='discord-1')
        older_run = self.fetch_mee6_run([mee6_player('discord-1', 100)])
        newer_run = self.fetch_mee6_run([mee6_player('discord-1', 150)])
        apply_sync_run(newer_run)

        with self.assertRaises(Mee6SyncError):
            apply_sync_run(older_run)

    @override_settings(CRON_SYNC_TOKEN='test-cron-token')
    def test_cron_endpoint_requires_token(self):
        response = self.api_client.post('/api/v1/community-xp/mee6/sync-and-apply/')

        self.assertEqual(response.status_code, 403)

    @override_settings(CRON_SYNC_TOKEN='test-cron-token')
    @patch('community_xp.views.threading.Thread')
    def test_cron_endpoint_starts_background_fetch_and_apply(self, thread_mock):
        thread_instance = Mock()
        thread_mock.return_value = thread_instance

        response = self.api_client.post(
            '/api/v1/community-xp/mee6/sync-and-apply/',
            HTTP_X_CRON_TOKEN='test-cron-token',
        )

        self.assertEqual(response.status_code, 202)
        thread_mock.assert_called_once()
        thread_instance.start.assert_called_once()
        _, kwargs = thread_mock.call_args
        self.assertTrue(kwargs['daemon'])
        self.assertEqual(kwargs['kwargs']['guild_id'], None)
        self.assertEqual(kwargs['kwargs']['page_size'], None)
        self.assertTrue(kwargs['kwargs']['owner_token'])

    @patch('community_xp.views.apply_sync_run')
    @patch('community_xp.views.run_mee6_sync')
    def test_fetch_and_apply_helper_applies_fetched_snapshot(self, run_mee6_sync_mock, apply_sync_run_mock):
        from community_xp.views import _run_mee6_fetch_and_apply

        run = Mee6SyncRun.objects.create(
            guild_id='guild-1',
            page_size=1000,
            status=Mee6SyncRun.STATUS_SUCCESS,
            completed_at=timezone.now(),
        )
        run_mee6_sync_mock.return_value = {
            'run_id': run.id,
            'players_fetched': 1,
            'matched_players': 1,
            'unmatched_players': 0,
            'pages_fetched': 1,
        }
        apply_sync_run_mock.return_value = {
            'run_id': run.id,
            'players_applied': 1,
            'matched_players': 1,
            'unmatched_players': 0,
        }

        fetch_result, apply_result = _run_mee6_fetch_and_apply()

        self.assertEqual(fetch_result['run_id'], run.pk)
        self.assertEqual(apply_result['run_id'], run.pk)
        run_mee6_sync_mock.assert_called_once_with(
            guild_id=None,
            page_size=None,
            use_lock=False,
        )
        self.assertEqual(apply_sync_run_mock.call_args.args[0].pk, run.pk)
