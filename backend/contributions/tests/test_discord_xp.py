from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from contributions.models import (
    Category,
    Contribution,
    ContributionDiscordXPState,
    ContributionType,
    DiscordXPDistributionEvent,
    Evidence,
)
from leaderboard.models import GlobalLeaderboardMultiplier
from social_connections.encryption import encrypt_token
from social_connections.models import DiscordConnection
from stewards.models import Steward, StewardPermission

User = get_user_model()


class StewardDiscordXPTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        now = timezone.now()

        self.community_category = Category.objects.create(
            name='Community',
            slug='community',
        )
        self.builder_category = Category.objects.create(
            name='Builder',
            slug='builder',
        )
        self.community_type = ContributionType.objects.create(
            name='Community Call',
            slug='community-call',
            category=self.community_category,
            min_points=0,
            max_points=500,
        )
        self.other_type = ContributionType.objects.create(
            name='Builder Post',
            slug='builder-post',
            category=self.builder_category,
            min_points=0,
            max_points=500,
        )
        for contribution_type in [self.community_type, self.other_type]:
            GlobalLeaderboardMultiplier.objects.create(
                contribution_type=contribution_type,
                multiplier_value=1,
                valid_from=now - timedelta(days=1),
            )

        self.user = User.objects.create_user(
            email='alice@example.com',
            address='0x1111111111111111111111111111111111111111',
            password='testpass123',
            name='Alice',
        )
        self.other_user = User.objects.create_user(
            email='bob@example.com',
            address='0x2222222222222222222222222222222222222222',
            password='testpass123',
            name='Bob',
        )
        self.steward_user = User.objects.create_user(
            email='steward@example.com',
            address='0x3333333333333333333333333333333333333333',
            password='testpass123',
            name='Steward',
        )
        self.steward = Steward.objects.create(user=self.steward_user)
        StewardPermission.objects.create(
            steward=self.steward,
            contribution_type=self.community_type,
            action='accept',
        )
        self.client.force_authenticate(user=self.steward_user)

    def create_contribution(self, *, user=None, contribution_type=None, points=50, title='Community update', notes='GenLayer update notes'):
        return Contribution.objects.create(
            user=user or self.user,
            contribution_type=contribution_type or self.community_type,
            points=points,
            contribution_date=timezone.now(),
            title=title,
            notes=notes,
        )

    def link_discord(self, user=None, username='alice_discord', platform_user_id='999'):
        return DiscordConnection.objects.create(
            user=user or self.user,
            platform_user_id=platform_user_id,
            platform_username=username,
            access_token=encrypt_token('discord-access-token'),
            linked_at=timezone.now(),
            guild_member=True,
        )

    def test_community_contributions_create_xp_state_only_for_community(self):
        community_contribution = self.create_contribution(points=40)
        other_contribution = self.create_contribution(
            contribution_type=self.other_type,
            points=40,
            title='Builder post',
        )

        self.assertTrue(
            ContributionDiscordXPState.objects.filter(contribution=community_contribution).exists()
        )
        self.assertFalse(
            ContributionDiscordXPState.objects.filter(contribution=other_contribution).exists()
        )

        with self.assertRaises(ValidationError):
            ContributionDiscordXPState.objects.create(contribution=other_contribution)

    def test_xp_list_is_community_only_positive_points_and_searchable(self):
        self.link_discord(username='alice_xp')
        contribution = self.create_contribution(points=80, title='Deep community thread')
        Evidence.objects.create(
            contribution=contribution,
            url='https://example.com/deep-thread',
            description='forum evidence',
        )
        zero = self.create_contribution(
            user=self.other_user,
            points=0,
            title='Zero point community note',
        )

        response = self.client.get('/api/v1/steward-discord-xp/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['contribution'], contribution.id)
        self.assertNotEqual(response.data['results'][0]['contribution'], zero.id)

        response = self.client.get('/api/v1/steward-discord-xp/', {'status': 'pending'})
        self.assertEqual(response.data['count'], 1)

        response = self.client.get('/api/v1/steward-discord-xp/', {'username_search': 'alice_xp'})
        self.assertEqual(response.data['count'], 1)

        response = self.client.get('/api/v1/steward-discord-xp/', {'include_content': 'deep-thread'})
        self.assertEqual(response.data['count'], 1)

        response = self.client.get('/api/v1/steward-discord-xp/', {'exclude_content': 'deep'})
        self.assertEqual(response.data['count'], 0)

    def test_zero_point_overdistributed_state_remains_visible_and_unsettable(self):
        self.link_discord(username='alice_xp')
        contribution = self.create_contribution(points=30)
        state = contribution.discord_xp_state
        state.awarded_amount = 30
        state.distributed_at = timezone.now()
        state.distributed_by = self.steward_user
        state.status = ContributionDiscordXPState.STATUS_DISTRIBUTED
        state.save()

        contribution.points = 0
        contribution.frozen_global_points = 0
        contribution.save()
        state.refresh_from_db()
        self.assertEqual(state.status, ContributionDiscordXPState.STATUS_NEEDS_REVIEW)

        response = self.client.get('/api/v1/steward-discord-xp/', {'status': 'needs_review'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['contribution'], contribution.id)

        response = self.client.post(f'/api/v1/steward-discord-xp/{contribution.id}/unset-distributed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        state.refresh_from_db()
        self.assertEqual(state.status, ContributionDiscordXPState.STATUS_PENDING)
        self.assertEqual(state.awarded_amount, 0)

    @patch('social_connections.oauth_service.requests')
    def test_record_copy_refreshes_discord_username_and_updates_copy_state(self, mock_requests):
        self.link_discord(username='alice_xp')
        contribution = self.create_contribution(points=75)
        user_response = MagicMock()
        user_response.raise_for_status = MagicMock()
        user_response.json.return_value = {
            'id': '999',
            'username': 'alice_latest',
            'discriminator': '0',
            'avatar': 'avatar-hash',
        }
        mock_requests.get.return_value = user_response

        response = self.client.post(f'/api/v1/steward-discord-xp/{contribution.id}/record-copy/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        state = contribution.discord_xp_state
        state.refresh_from_db()
        self.assertEqual(state.status, ContributionDiscordXPState.STATUS_PENDING)
        self.assertEqual(state.awarded_amount, 0)
        self.assertEqual(state.last_copied_by, self.steward_user)
        self.assertIsNotNone(state.last_copied_at)
        self.user.discordconnection.refresh_from_db()
        self.assertEqual(self.user.discordconnection.platform_username, 'alice_latest')
        self.assertEqual(response.data['command'], '/give-xp member:@alice_latest amount:75')

        event = DiscordXPDistributionEvent.objects.get(state=state)
        self.assertEqual(event.action, DiscordXPDistributionEvent.ACTION_COPIED)
        self.assertEqual(event.amount, 75)

    @patch('social_connections.oauth_service.requests')
    def test_record_copy_rejects_discord_account_mismatch(self, mock_requests):
        self.link_discord(username='alice_xp', platform_user_id='999')
        contribution = self.create_contribution(points=75)
        user_response = MagicMock()
        user_response.raise_for_status = MagicMock()
        user_response.json.return_value = {
            'id': 'different-discord-id',
            'username': 'alice_latest',
            'discriminator': '0',
            'avatar': 'avatar-hash',
        }
        mock_requests.get.return_value = user_response

        response = self.client.post(f'/api/v1/steward-discord-xp/{contribution.id}/record-copy/')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('Discord account mismatch', response.data['detail'])
        self.assertFalse(DiscordXPDistributionEvent.objects.filter(state=contribution.discord_xp_state).exists())

    def test_mark_and_unset_distribution_flag_are_audited(self):
        self.link_discord(username='alice_xp')
        contribution = self.create_contribution(points=30)

        response = self.client.post(f'/api/v1/steward-discord-xp/{contribution.id}/mark-distributed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        state = contribution.discord_xp_state
        state.refresh_from_db()
        self.assertEqual(state.status, ContributionDiscordXPState.STATUS_DISTRIBUTED)
        self.assertEqual(state.awarded_amount, 30)
        self.assertEqual(state.distributed_by, self.steward_user)

        response = self.client.post(f'/api/v1/steward-discord-xp/{contribution.id}/unset-distributed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        state.refresh_from_db()
        self.assertEqual(state.status, ContributionDiscordXPState.STATUS_PENDING)
        self.assertEqual(state.awarded_amount, 0)
        self.assertIsNone(state.distributed_by)

        actions = list(
            DiscordXPDistributionEvent.objects.filter(state=state)
            .order_by('created_at')
            .values_list('action', flat=True)
        )
        self.assertEqual(actions, [
            DiscordXPDistributionEvent.ACTION_DISTRIBUTED,
            DiscordXPDistributionEvent.ACTION_UNSET,
        ])

    def test_point_changes_create_pending_delta_or_needs_review(self):
        contribution = self.create_contribution(points=40)
        state = contribution.discord_xp_state
        state.awarded_amount = 40
        state.status = ContributionDiscordXPState.STATUS_DISTRIBUTED
        state.save(update_fields=['awarded_amount', 'status', 'updated_at'])

        contribution.frozen_global_points = 70
        contribution.save(update_fields=['frozen_global_points', 'updated_at'])
        state.refresh_from_db()
        self.assertEqual(state.status, ContributionDiscordXPState.STATUS_PENDING)
        self.assertEqual(state.pending_amount, 30)

        contribution.frozen_global_points = 25
        contribution.save(update_fields=['frozen_global_points', 'updated_at'])
        state.refresh_from_db()
        self.assertEqual(state.status, ContributionDiscordXPState.STATUS_NEEDS_REVIEW)
        self.assertEqual(state.pending_amount, 0)
