from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from community_xp.models import Mee6CurrentXP, Mee6SyncRun
from contributions.models import Category
from poaps.models import PoapClaim, PoapDrop
from social_connections.discord_oauth import (
    DISCORD_EARNED_ROLE_LOCK_NAME,
    _acquire_role_sync_lock,
)
from social_connections.discord_roles import (
    DiscordRoleSyncService,
    DiscordRoleSyncUnavailable,
)
from social_connections.earned_roles import (
    BRAIN_CP,
    BRAIN_POAPS,
    SYNAPSE_CP,
    SYNAPSE_POAPS,
    assign_earned_community_roles,
)
from social_connections.models import (
    DiscordConnection,
    DiscordEarnedRoleAssignment,
    DiscordRole,
)
from social_tasks.models import SocialTask, SocialTaskCompletion
from users.models import User


def mock_response(status_code=200, payload=None, headers=None):
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {}
    response.json.return_value = payload if payload is not None else {}
    return response


ROLE_SETTINGS = {
    'DISCORD_GUILD_ID': 'guild-1',
    'DISCORD_BOT_TOKEN': 'bot-token',
    'DISCORD_SYNAPSE_ROLE_ID': 'role-synapse',
    'DISCORD_BRAIN_ROLE_ID': 'role-brain',
    'DISCORD_NEUROCREATIVE_ROLE_ID': 'role-neuro',
}


@override_settings(DISCORD_GUILD_ID='guild-1', DISCORD_BOT_TOKEN='bot-token')
class AddMemberRoleTest(TestCase):
    def setUp(self):
        self.service = DiscordRoleSyncService()

    @patch('social_connections.discord_roles.requests.request')
    def test_204_assigns(self, mock_request):
        mock_request.return_value = mock_response(204)

        self.assertTrue(self.service.add_member_role('user-1', 'role-1'))

        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], 'PUT')
        self.assertEqual(
            args[1],
            'https://discord.com/api/v10/guilds/guild-1/members/user-1/roles/role-1',
        )

    @patch('social_connections.discord_roles.requests.request')
    def test_sends_audit_log_reason(self, mock_request):
        mock_request.return_value = mock_response(204)

        self.service.add_member_role('user-1', 'role-1', audit_log_reason='Earned role: synapse')

        self.assertEqual(
            mock_request.call_args.kwargs['headers']['X-Audit-Log-Reason'],
            'Earned%20role%3A%20synapse',
        )

    @patch('social_connections.discord_roles.requests.request')
    def test_404_returns_false(self, mock_request):
        mock_request.return_value = mock_response(404)

        self.assertFalse(self.service.add_member_role('user-1', 'role-1'))

    @patch('social_connections.discord_roles.requests.request')
    def test_403_raises_unavailable(self, mock_request):
        mock_request.return_value = mock_response(403)

        with self.assertRaises(DiscordRoleSyncUnavailable) as ctx:
            self.service.add_member_role('user-1', 'role-1')
        self.assertEqual(ctx.exception.status_code, 403)

    @patch('social_connections.discord_roles.time.sleep')
    @patch('social_connections.discord_roles.requests.request')
    def test_short_rate_limit_retries_once(self, mock_request, mock_sleep):
        mock_request.side_effect = [
            mock_response(429, headers={'Retry-After': '1'}),
            mock_response(204),
        ]

        self.assertTrue(self.service.add_member_role('user-1', 'role-1'))
        self.assertEqual(mock_request.call_count, 2)


@override_settings(**ROLE_SETTINGS)
class AssignEarnedCommunityRolesTest(TestCase):
    def setUp(self):
        self.sync_run = Mee6SyncRun.objects.create(
            guild_id='guild-1',
            status=Mee6SyncRun.STATUS_SUCCESS,
            completed_at=timezone.now(),
            applied_at=timezone.now(),
        )
        self.drop_counter = 0

    def make_user(self, email, xp, poaps=0, guild_member=True, held_role_ids=()):
        user = User.objects.create_user(email=email, password='testpass123', name=email.split('@')[0])
        Mee6CurrentXP.objects.create(
            guild_id='guild-1',
            discord_id=f'discord-{user.id}',
            rank=user.id,
            xp=xp,
            sync_run=self.sync_run,
            synced_at=timezone.now(),
            matched_user=user,
        )
        connection = DiscordConnection.objects.create(
            user=user,
            platform_user_id=f'discord-{user.id}',
            platform_username=f'discord-{user.id}',
            linked_at=timezone.now(),
            guild_member=guild_member,
        )
        for role_id in held_role_ids:
            role, _ = DiscordRole.objects.get_or_create(
                guild_id='guild-1',
                role_id=role_id,
                defaults={'name': role_id},
            )
            connection.current_roles.add(role)
        for _ in range(poaps):
            self.drop_counter += 1
            drop = PoapDrop.objects.create(
                title=f'Drop {self.drop_counter}',
                event_start_at=timezone.now(),
            )
            PoapClaim.objects.create(drop=drop, user=user, claim_method=PoapClaim.CLAIM_ADMIN)
        return user, connection

    @patch('social_connections.discord_roles.requests.request')
    def test_assigns_synapse_at_thresholds(self, mock_request):
        mock_request.return_value = mock_response(204)
        user, connection = self.make_user('synapse@test.com', SYNAPSE_CP, poaps=SYNAPSE_POAPS)

        stats = assign_earned_community_roles()

        self.assertEqual(stats['synapse_assigned'], 1)
        self.assertEqual(stats['brain_assigned'], 0)
        self.assertEqual(stats['errors'], 0)
        self.assertEqual(mock_request.call_count, 1)
        self.assertIn('role-synapse', args_url := mock_request.call_args[0][1])
        self.assertIn(f'discord-{user.id}', args_url)
        self.assertTrue(connection.current_roles.filter(role_id='role-synapse').exists())
        self.assertEqual(stats['assignments'][0]['role'], 'synapse')
        assignment = DiscordEarnedRoleAssignment.objects.get()
        self.assertEqual(assignment.connection, connection)
        self.assertEqual(assignment.discord_user_id, f'discord-{user.id}')
        self.assertEqual(assignment.role_id, 'role-synapse')
        self.assertEqual(assignment.role_name, 'synapse')
        self.assertEqual(assignment.total_points, SYNAPSE_CP)
        self.assertEqual(assignment.poap_count, SYNAPSE_POAPS)
        self.assertIsNotNone(assignment.created_at)

    @patch('social_connections.discord_roles.requests.request')
    def test_pending_social_task_points_count_toward_synapse(self, mock_request):
        mock_request.return_value = mock_response(204)
        user, _ = self.make_user(
            'synapse-social-task@test.com',
            SYNAPSE_CP - 500,
            poaps=SYNAPSE_POAPS,
        )
        category, _ = Category.objects.get_or_create(
            slug='community',
            defaults={'name': 'Community'},
        )
        task = SocialTask.objects.create(
            slug='synapse-social-task',
            name='Synapse social task',
            category=category,
            points=500,
            verification_type='click_through',
            action_url='https://example.com',
        )
        SocialTaskCompletion.objects.create(
            user=user,
            task=task,
            points_awarded=500,
            verification_type='click_through',
        )

        stats = assign_earned_community_roles()

        self.assertEqual(stats['synapse_assigned'], 1)
        self.assertEqual(stats['assignments'][0]['total_points'], SYNAPSE_CP)

    @patch('social_connections.discord_roles.requests.request')
    def test_below_poap_threshold_assigns_nothing(self, mock_request):
        self.make_user('few-poaps@test.com', SYNAPSE_CP, poaps=SYNAPSE_POAPS - 1)

        stats = assign_earned_community_roles()

        self.assertEqual(stats['synapse_assigned'], 0)
        mock_request.assert_not_called()

    @patch('social_connections.discord_roles.requests.request')
    def test_below_cp_threshold_not_a_candidate(self, mock_request):
        self.make_user('low-cp@test.com', SYNAPSE_CP - 1, poaps=SYNAPSE_POAPS)

        stats = assign_earned_community_roles()

        self.assertEqual(stats['checked'], 0)
        mock_request.assert_not_called()

    @patch('social_connections.discord_roles.requests.request')
    def test_brain_requires_neurocreative_role(self, mock_request):
        mock_request.return_value = mock_response(204)
        self.make_user(
            'no-neuro@test.com',
            BRAIN_CP,
            poaps=BRAIN_POAPS,
            held_role_ids=('role-synapse',),
        )

        stats = assign_earned_community_roles()

        self.assertEqual(stats['brain_assigned'], 0)
        self.assertEqual(stats['synapse_assigned'], 0)
        mock_request.assert_not_called()

    @patch('social_connections.discord_roles.requests.request')
    def test_brain_assigned_with_neurocreative(self, mock_request):
        mock_request.return_value = mock_response(204)
        user, connection = self.make_user(
            'brain@test.com',
            BRAIN_CP,
            poaps=BRAIN_POAPS,
            held_role_ids=('role-synapse', 'role-neuro'),
        )

        stats = assign_earned_community_roles()

        self.assertEqual(stats['brain_assigned'], 1)
        self.assertEqual(stats['synapse_assigned'], 0)
        self.assertTrue(connection.current_roles.filter(role_id='role-brain').exists())

    @patch('social_connections.discord_roles.requests.request')
    def test_already_held_role_not_reassigned(self, mock_request):
        self.make_user(
            'held@test.com',
            SYNAPSE_CP,
            poaps=SYNAPSE_POAPS,
            held_role_ids=('role-synapse',),
        )

        stats = assign_earned_community_roles()

        self.assertEqual(stats['synapse_assigned'], 0)
        mock_request.assert_not_called()

    @patch('social_connections.discord_roles.requests.request')
    def test_non_guild_member_skipped(self, mock_request):
        self.make_user('left@test.com', SYNAPSE_CP, poaps=SYNAPSE_POAPS, guild_member=False)

        stats = assign_earned_community_roles()

        self.assertEqual(stats['skipped_not_member'], 1)
        self.assertEqual(stats['synapse_assigned'], 0)
        mock_request.assert_not_called()

    @patch('social_connections.discord_roles.requests.request')
    def test_dry_run_makes_no_requests(self, mock_request):
        user, connection = self.make_user('dry@test.com', SYNAPSE_CP, poaps=SYNAPSE_POAPS)

        stats = assign_earned_community_roles(dry_run=True)

        self.assertEqual(stats['synapse_assigned'], 1)
        self.assertEqual(len(stats['assignments']), 1)
        mock_request.assert_not_called()
        self.assertFalse(connection.current_roles.filter(role_id='role-synapse').exists())
        self.assertFalse(DiscordEarnedRoleAssignment.objects.exists())

    @patch('social_connections.discord_roles.requests.request')
    def test_unconfigured_role_ids_noop(self, mock_request):
        self.make_user('unconfigured@test.com', SYNAPSE_CP, poaps=SYNAPSE_POAPS)

        with override_settings(DISCORD_BRAIN_ROLE_ID=''):
            stats = assign_earned_community_roles()

        self.assertEqual(stats['checked'], 0)
        mock_request.assert_not_called()

    @patch('social_connections.discord_roles.requests.request')
    def test_rate_limit_aborts_run(self, mock_request):
        mock_request.return_value = mock_response(429, headers={'Retry-After': '30'})
        self.make_user('rl-a@test.com', SYNAPSE_CP, poaps=SYNAPSE_POAPS)
        self.make_user('rl-b@test.com', SYNAPSE_CP, poaps=SYNAPSE_POAPS)

        stats = assign_earned_community_roles()

        self.assertTrue(stats['aborted'])
        self.assertEqual(stats['synapse_assigned'], 0)
        self.assertEqual(stats['errors'], 1)
        self.assertEqual(mock_request.call_count, 1)

    @patch('social_connections.discord_roles.requests.request')
    def test_transient_error_continues_with_next_user(self, mock_request):
        mock_request.side_effect = [mock_response(500), mock_response(204)]
        self.make_user('flaky-a@test.com', SYNAPSE_CP, poaps=SYNAPSE_POAPS)
        self.make_user('flaky-b@test.com', SYNAPSE_CP, poaps=SYNAPSE_POAPS)

        stats = assign_earned_community_roles()

        self.assertFalse(stats['aborted'])
        self.assertEqual(stats['errors'], 1)
        self.assertEqual(stats['synapse_assigned'], 1)

    @patch('social_connections.discord_roles.requests.request')
    def test_member_left_between_queries_skipped(self, mock_request):
        mock_request.return_value = mock_response(404)
        user, connection = self.make_user('gone@test.com', SYNAPSE_CP, poaps=SYNAPSE_POAPS)

        stats = assign_earned_community_roles()

        self.assertEqual(stats['synapse_assigned'], 0)
        self.assertEqual(stats['skipped_not_member'], 1)
        self.assertFalse(connection.current_roles.filter(role_id='role-synapse').exists())


@override_settings(**ROLE_SETTINGS, CRON_SYNC_TOKEN='cron-token')
class AssignEarnedRolesEndpointTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/v1/users/discord/assign-earned-roles/'

    def test_requires_cron_token(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)

    def test_conflict_while_lock_held(self):
        lock_token, _ = _acquire_role_sync_lock(DISCORD_EARNED_ROLE_LOCK_NAME)
        self.assertIsNotNone(lock_token)

        response = self.client.post(self.url, HTTP_X_CRON_TOKEN='cron-token')

        self.assertEqual(response.status_code, 409)

    @patch('social_connections.discord_oauth.threading.Thread')
    def test_accepted_with_token(self, mock_thread):
        response = self.client.post(self.url, HTTP_X_CRON_TOKEN='cron-token')

        self.assertEqual(response.status_code, 202)
        self.assertEqual(mock_thread.call_count, 2)
