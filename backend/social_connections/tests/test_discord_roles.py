from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from users.models import User
from social_connections.discord_roles import (
    DiscordRoleSyncService,
    DiscordRoleSyncUnavailable,
)
from social_connections.models import DiscordConnection, DiscordRole


def mock_response(status_code=200, payload=None, headers=None):
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {}
    response.json.return_value = payload if payload is not None else {}
    return response


@override_settings(
    DISCORD_GUILD_ID='guild-1',
    DISCORD_BOT_TOKEN='bot-token',
    DISCORD_MANUAL_ROLE_SYNC_COOLDOWN_SECONDS=30,
)
class DiscordRoleSyncServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='discord-role@test.com',
            password='testpass123',
            name='Discord Role User',
        )
        self.connection = DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='user-1',
            platform_username='discorduser',
            linked_at=timezone.now(),
        )
        self.service = DiscordRoleSyncService()

    @patch('social_connections.discord_roles.requests.request')
    def test_sync_role_catalog_upserts_and_marks_deleted(self, mock_request):
        old_role = DiscordRole.objects.create(
            guild_id='guild-1',
            role_id='old-role',
            name='Old',
        )
        mock_request.return_value = mock_response(200, [
            {
                'id': 'guild-1',
                'name': '@everyone',
                'color': 0,
                'position': 0,
            },
            {
                'id': 'role-1',
                'name': 'Builder',
                'color': 5793266,
                'position': 3,
                'hoist': True,
                'managed': False,
                'mentionable': True,
            },
        ])

        roles = self.service.sync_role_catalog()

        self.assertEqual(len(roles), 2)
        role = DiscordRole.objects.get(role_id='role-1')
        self.assertEqual(role.name, 'Builder')
        self.assertEqual(role.color, 5793266)
        self.assertEqual(role.position, 3)
        self.assertTrue(role.hoist)
        self.assertTrue(role.mentionable)
        old_role.refresh_from_db()
        self.assertIsNotNone(old_role.deleted_at)

    @patch('social_connections.discord_roles.requests.request')
    def test_sync_member_roles_records_roles(self, mock_request):
        mock_request.side_effect = [
            mock_response(200, [
                {'id': 'role-1', 'name': 'Builder', 'color': 1, 'position': 2},
                {'id': 'role-2', 'name': 'Validator', 'color': 2, 'position': 1},
            ]),
            mock_response(200, {
                'roles': ['role-1'],
                'joined_at': '2025-01-01T00:00:00+00:00',
                'nick': 'Builder Nick',
            }),
        ]

        result = self.service.sync_member_roles(self.connection)

        self.assertTrue(result.is_member)
        self.connection.refresh_from_db()
        self.assertTrue(self.connection.guild_member)
        self.assertEqual(self.connection.guild_nick, 'Builder Nick')
        self.assertEqual(
            set(self.connection.current_roles.values_list('role_id', flat=True)),
            {'role-1'},
        )

    @patch('social_connections.discord_roles.requests.request')
    def test_sync_member_roles_clears_roles_when_not_in_guild(self, mock_request):
        role = DiscordRole.objects.create(
            guild_id='guild-1',
            role_id='role-1',
            name='Builder',
        )
        self.connection.current_roles.add(role)
        self.connection.guild_member = True
        self.connection.save(update_fields=['guild_member'])
        mock_request.side_effect = [
            mock_response(200, [{'id': 'role-1', 'name': 'Builder'}]),
            mock_response(404, {'message': 'Unknown Member'}),
        ]

        result = self.service.sync_member_roles(self.connection)

        self.assertFalse(result.is_member)
        self.connection.refresh_from_db()
        self.assertFalse(self.connection.guild_member)
        self.assertEqual(self.connection.current_roles.count(), 0)

    @patch('social_connections.discord_roles.requests.request')
    def test_request_exception_becomes_unavailable(self, mock_request):
        mock_request.side_effect = requests.Timeout('timed out')

        with self.assertRaises(DiscordRoleSyncUnavailable):
            self.service.sync_role_catalog()


@override_settings(
    DISCORD_GUILD_ID='guild-1',
    DISCORD_BOT_TOKEN='bot-token',
    DISCORD_MANUAL_ROLE_SYNC_COOLDOWN_SECONDS=30,
)
class DiscordRoleManualRefreshTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='manual-refresh@test.com',
            password='testpass123',
            name='Manual Refresh User',
        )
        self.connection = DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='user-1',
            platform_username='discorduser',
            linked_at=timezone.now(),
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch('social_connections.discord_oauth.DiscordRoleSyncService')
    def test_manual_refresh_success_updates_user_payload(self, mock_service_class):
        role = DiscordRole.objects.create(
            guild_id='guild-1',
            role_id='role-1',
            name='Builder',
            position=2,
        )
        self.connection.current_roles.add(role)
        service = mock_service_class.return_value
        service.sync_member_roles.return_value = MagicMock(
            connection=self.connection,
            is_member=True,
        )

        response = self.client.post('/api/v1/users/discord/sync-roles/me/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['cooldown_active'])
        self.assertIn('user', response.data)
        self.assertEqual(
            response.data['discord_connection']['roles'][0]['role_id'],
            'role-1',
        )
        self.connection.refresh_from_db()
        self.assertIsNotNone(self.connection.roles_manual_synced_at)

    def test_manual_refresh_cooldown_returns_cached_connection(self):
        self.connection.roles_manual_synced_at = timezone.now()
        self.connection.save(update_fields=['roles_manual_synced_at'])

        response = self.client.post('/api/v1/users/discord/sync-roles/me/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['cooldown_active'])
        self.assertIn('next_allowed_at', response.data)
