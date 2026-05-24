from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import Category, ContributionType, SubmittedContribution
from social_connections.models import DiscordConnection, DiscordRole

User = get_user_model()


@override_settings(
    DISCORD_GUILD_ID='guild-1',
    DISCORD_BOT_TOKEN='bot-token',
    DISCORD_ROLE_SUBMISSION_SYNC_GRACE_SECONDS=30,
)
class DiscordRoleSubmissionGatingTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Community',
            slug='community-test',
            description='Community test category',
        )
        self.contribution_type = ContributionType.objects.create(
            name='Role Gated Type',
            slug='role-gated-type',
            description='Requires a Discord role',
            category=self.category,
            min_points=1,
            max_points=10,
        )
        self.required_role = DiscordRole.objects.create(
            guild_id='guild-1',
            role_id='role-1',
            name='Builder',
            position=2,
        )
        self.contribution_type.required_discord_roles.add(self.required_role)
        self.ungated_type = ContributionType.objects.create(
            name='Ungated Type',
            slug='ungated-type',
            description='Does not require a Discord role',
            category=self.category,
            min_points=1,
            max_points=10,
        )

        self.user = User.objects.create_user(
            email='discord-gate@test.com',
            address='0x1234567890123456789012345678901234567890',
            password='testpass123',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.recaptcha_patcher = patch(
            'contributions.recaptcha_field.ReCaptchaField.to_internal_value',
            return_value='test-token',
        )
        self.recaptcha_patcher.start()
        self.addCleanup(self.recaptcha_patcher.stop)

    def _post_submission(self):
        return self.client.post(
            '/api/v1/submissions/',
            {
                'contribution_type': self.contribution_type.id,
                'contribution_date': timezone.now().date().isoformat(),
                'notes': 'Role gated submission',
                'recaptcha': 'test-token',
                'evidence_items': [
                    {
                        'description': 'Evidence',
                        'url': 'https://example.com/discord-role-gated-evidence',
                    },
                ],
            },
            format='json',
        )

    def _create_pending_submission(self, contribution_type=None):
        return SubmittedContribution.objects.create(
            user=self.user,
            contribution_type=contribution_type or self.ungated_type,
            contribution_date=timezone.now(),
            notes='Pending submission',
        )

    def test_blocks_user_without_discord_connection(self):
        response = self._post_submission()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('link your Discord', response.data['error'])

    def test_blocks_edit_to_role_gated_type_without_discord_role(self):
        submission = self._create_pending_submission()

        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            {
                'contribution_type': self.contribution_type.id,
                'notes': 'Attempted gated edit',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('link your Discord', response.data['error'])
        submission.refresh_from_db()
        self.assertEqual(submission.contribution_type_id, self.ungated_type.id)

    def test_blocks_edit_of_existing_role_gated_type_without_discord_role(self):
        submission = self._create_pending_submission(self.contribution_type)

        response = self.client.patch(
            f'/api/v1/submissions/{submission.id}/',
            {'notes': 'Attempted notes edit'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('link your Discord', response.data['error'])

    def test_blocks_user_missing_required_role_after_refresh(self):
        connection = DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='discord-user',
            platform_username='discorduser',
            linked_at=timezone.now(),
        )
        connection.guild_member = True
        connection.roles_synced_at = timezone.now()
        connection.save(update_fields=['guild_member', 'roles_synced_at'])

        response = self._post_submission()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Discord roles', response.data['error'])

    def test_allows_user_with_required_role(self):
        connection = DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='discord-user',
            platform_username='discorduser',
            guild_member=True,
            roles_synced_at=timezone.now(),
            linked_at=timezone.now(),
        )
        connection.current_roles.add(self.required_role)

        response = self._post_submission()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('social_connections.discord_roles.DiscordRoleSyncService.sync_member_roles')
    def test_refresh_failure_fails_closed(self, mock_sync_member_roles):
        DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='discord-user',
            platform_username='discorduser',
            linked_at=timezone.now(),
        )
        from social_connections.discord_roles import DiscordRoleSyncUnavailable

        mock_sync_member_roles.side_effect = DiscordRoleSyncUnavailable('rate limited')

        response = self._post_submission()

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn('temporarily unavailable', response.data['error'])
