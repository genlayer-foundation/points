from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
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
from social_tasks.models import SocialTask, SocialTaskCompletion
from stewards.models import Steward, StewardPermission

User = get_user_model()


def state_id(source):
    """Discord XP state id for a contribution or social task completion."""
    return ContributionDiscordXPState.objects.get(
        Q(contribution=source) if isinstance(source, Contribution)
        else Q(social_task_completion=source)
    ).id


class StewardDiscordXPTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        now = timezone.now()

        self.community_category, _ = Category.objects.get_or_create(
            slug='community',
            defaults={
                'name': 'Community',
            },
        )
        self.builder_category, _ = Category.objects.get_or_create(
            slug='builder',
            defaults={
                'name': 'Builder',
            },
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

    def link_discord(self, user=None, username='alice_discord', platform_user_id='999', guild_member=True):
        return DiscordConnection.objects.create(
            user=user or self.user,
            platform_user_id=platform_user_id,
            platform_username=username,
            access_token=encrypt_token('discord-access-token'),
            linked_at=timezone.now(),
            guild_member=guild_member,
        )

    def create_social_task(self, *, category=None, name='Follow GenLayer', slug='follow-genlayer', points=10):
        return SocialTask.objects.create(
            name=name,
            slug=slug,
            category=category or self.community_category,
            points=points,
            verification_type='click_through',
            action_url='https://example.com/task',
        )

    def complete_social_task(self, task, *, user=None, points=None):
        return SocialTaskCompletion.objects.create(
            user=user or self.user,
            task=task,
            points_awarded=points if points is not None else task.points,
            verification_type=task.verification_type,
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
        unconfirmed_user = User.objects.create_user(
            email='unconfirmed@example.com',
            address='0x4444444444444444444444444444444444444444',
            password='testpass123',
            name='Unconfirmed',
        )
        self.link_discord(
            user=unconfirmed_user,
            username='unconfirmed_xp',
            platform_user_id='1000',
            guild_member=False,
        )
        unconfirmed = self.create_contribution(
            user=unconfirmed_user,
            points=90,
            title='Unconfirmed guild member note',
        )

        response = self.client.get('/api/v1/steward-discord-xp/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['contribution'], contribution.id)
        self.assertNotEqual(response.data['results'][0]['contribution'], zero.id)
        self.assertNotEqual(response.data['results'][0]['contribution'], unconfirmed.id)

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

        response = self.client.post(f'/api/v1/steward-discord-xp/{state_id(contribution)}/unset-distributed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        state.refresh_from_db()
        self.assertEqual(state.status, ContributionDiscordXPState.STATUS_PENDING)
        self.assertEqual(state.awarded_amount, 0)

    def test_previously_awarded_non_member_remains_visible_and_unsettable(self):
        connection = self.link_discord(username='alice_xp')
        contribution = self.create_contribution(points=30)

        response = self.client.post(f'/api/v1/steward-discord-xp/{state_id(contribution)}/mark-distributed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        connection.guild_member = False
        connection.save(update_fields=['guild_member', 'updated_at'])
        contribution.points = 0
        contribution.frozen_global_points = 0
        contribution.save()
        contribution.discord_xp_state.refresh_from_db()
        self.assertEqual(contribution.discord_xp_state.status, ContributionDiscordXPState.STATUS_NEEDS_REVIEW)

        response = self.client.get('/api/v1/steward-discord-xp/', {'status': 'needs_review'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['contribution'], contribution.id)
        self.assertFalse(response.data['results'][0]['discord']['guild_member'])

        response = self.client.post(f'/api/v1/steward-discord-xp/{state_id(contribution)}/unset-distributed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        contribution.discord_xp_state.refresh_from_db()
        self.assertEqual(contribution.discord_xp_state.status, ContributionDiscordXPState.STATUS_PENDING)
        self.assertEqual(contribution.discord_xp_state.awarded_amount, 0)

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

        response = self.client.post(f'/api/v1/steward-discord-xp/{state_id(contribution)}/record-copy/')

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

        response = self.client.post(f'/api/v1/steward-discord-xp/{state_id(contribution)}/record-copy/')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('Discord account mismatch', response.data['detail'])
        self.assertFalse(DiscordXPDistributionEvent.objects.filter(state=contribution.discord_xp_state).exists())

    def test_mark_and_unset_distribution_flag_are_audited(self):
        self.link_discord(username='alice_xp')
        contribution = self.create_contribution(points=30)

        response = self.client.post(f'/api/v1/steward-discord-xp/{state_id(contribution)}/mark-distributed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        state = contribution.discord_xp_state
        state.refresh_from_db()
        self.assertEqual(state.status, ContributionDiscordXPState.STATUS_DISTRIBUTED)
        self.assertEqual(state.awarded_amount, 30)
        self.assertEqual(state.distributed_by, self.steward_user)

        response = self.client.post(f'/api/v1/steward-discord-xp/{state_id(contribution)}/unset-distributed/')
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

    def test_social_task_completion_creates_xp_state_only_for_community(self):
        community_task = self.create_social_task()
        builder_task = self.create_social_task(
            category=self.builder_category,
            name='Star the repo',
            slug='star-the-repo',
        )

        community_completion = self.complete_social_task(community_task)
        builder_completion = self.complete_social_task(builder_task, user=self.other_user)

        self.assertTrue(
            ContributionDiscordXPState.objects.filter(
                social_task_completion=community_completion
            ).exists()
        )
        self.assertFalse(
            ContributionDiscordXPState.objects.filter(
                social_task_completion=builder_completion
            ).exists()
        )

        with self.assertRaises(ValidationError):
            ContributionDiscordXPState.objects.create(social_task_completion=builder_completion)

    def test_social_task_completions_appear_in_xp_list(self):
        self.link_discord(username='alice_xp')
        task = self.create_social_task(points=10)
        completion = self.complete_social_task(task)

        # Guild-member requirement applies to social task rows too.
        non_member = User.objects.create_user(
            email='nonmember@example.com',
            address='0x5555555555555555555555555555555555555555',
            password='testpass123',
            name='NonMember',
        )
        self.link_discord(
            user=non_member,
            username='nonmember_xp',
            platform_user_id='1001',
            guild_member=False,
        )
        self.complete_social_task(task, user=non_member)

        response = self.client.get('/api/v1/steward-discord-xp/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        row = response.data['results'][0]
        self.assertEqual(row['source'], 'social_task')
        self.assertIsNone(row['contribution'])
        self.assertEqual(row['social_task']['slug'], task.slug)
        self.assertEqual(row['contribution_title'], task.name)
        self.assertEqual(row['frozen_global_points'], 10)
        self.assertEqual(row['pending_amount'], 10)
        self.assertEqual(row['command'], '/give-xp member:@alice_xp amount:10')
        self.assertIsNone(row['contribution_type'])

        # Search filters cover the task name and the recipient.
        response = self.client.get('/api/v1/steward-discord-xp/', {'include_content': 'Follow GenLayer'})
        self.assertEqual(response.data['count'], 1)
        response = self.client.get('/api/v1/steward-discord-xp/', {'username_search': 'alice_xp'})
        self.assertEqual(response.data['count'], 1)
        response = self.client.get('/api/v1/steward-discord-xp/', {'exclude_content': 'Follow'})
        self.assertEqual(response.data['count'], 0)

        # contribution+social rows can coexist in one list.
        self.create_contribution(points=40)
        response = self.client.get('/api/v1/steward-discord-xp/')
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(completion.discord_xp_state.status, ContributionDiscordXPState.STATUS_PENDING)

    def test_social_task_mark_and_unset_distribution_flag_are_audited(self):
        self.link_discord(username='alice_xp')
        task = self.create_social_task(points=10)
        completion = self.complete_social_task(task)

        response = self.client.post(
            f'/api/v1/steward-discord-xp/{state_id(completion)}/mark-distributed/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        state = completion.discord_xp_state
        state.refresh_from_db()
        self.assertEqual(state.status, ContributionDiscordXPState.STATUS_DISTRIBUTED)
        self.assertEqual(state.awarded_amount, 10)
        self.assertEqual(state.distributed_by, self.steward_user)

        response = self.client.post(
            f'/api/v1/steward-discord-xp/{state_id(completion)}/unset-distributed/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        state.refresh_from_db()
        self.assertEqual(state.status, ContributionDiscordXPState.STATUS_PENDING)
        self.assertEqual(state.awarded_amount, 0)

        actions = list(
            DiscordXPDistributionEvent.objects.filter(state=state)
            .order_by('created_at')
            .values_list('action', flat=True)
        )
        self.assertEqual(actions, [
            DiscordXPDistributionEvent.ACTION_DISTRIBUTED,
            DiscordXPDistributionEvent.ACTION_UNSET,
        ])

    @patch('social_connections.oauth_service.requests')
    def test_social_task_record_copy_updates_copy_state(self, mock_requests):
        self.link_discord(username='alice_xp')
        task = self.create_social_task(points=10)
        completion = self.complete_social_task(task)
        user_response = MagicMock()
        user_response.raise_for_status = MagicMock()
        user_response.json.return_value = {
            'id': '999',
            'username': 'alice_latest',
            'discriminator': '0',
            'avatar': 'avatar-hash',
        }
        mock_requests.get.return_value = user_response

        response = self.client.post(
            f'/api/v1/steward-discord-xp/{state_id(completion)}/record-copy/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        state = completion.discord_xp_state
        state.refresh_from_db()
        self.assertEqual(state.last_copied_by, self.steward_user)
        self.assertEqual(response.data['command'], '/give-xp member:@alice_latest amount:10')

    def test_social_task_rows_require_community_accept_permission(self):
        self.link_discord(username='alice_xp')
        task = self.create_social_task(points=10)
        completion = self.complete_social_task(task)

        builder_steward_user = User.objects.create_user(
            email='builder-steward@example.com',
            address='0x6666666666666666666666666666666666666666',
            password='testpass123',
            name='Builder Steward',
        )
        builder_steward = Steward.objects.create(user=builder_steward_user)
        StewardPermission.objects.create(
            steward=builder_steward,
            contribution_type=self.other_type,
            action='accept',
        )
        client = APIClient()
        client.force_authenticate(user=builder_steward_user)

        response = client.get('/api/v1/steward-discord-xp/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

        response = client.post(
            f'/api/v1/steward-discord-xp/{state_id(completion)}/mark-distributed/'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_numeric_state_id_returns_404(self):
        for action in ['record-copy', 'mark-distributed', 'unset-distributed']:
            response = self.client.post(f'/api/v1/steward-discord-xp/abc/{action}/')
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        response = self.client.get('/api/v1/steward-discord-xp/abc/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
