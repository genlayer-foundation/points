from datetime import timedelta

from django.test import TestCase
from django.db import IntegrityError
from django.utils import timezone

from users.models import User
from social_connections.models import (
    GitHubConnection, TwitterConnection, DiscordConnection, UsedOAuthCode
)


class SocialConnectionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            name='Test User',
        )
        self.user2 = User.objects.create_user(
            email='test2@example.com',
            password='testpass123',
            name='Test User 2',
        )

    def test_create_github_connection(self):
        conn = GitHubConnection.objects.create(
            user=self.user,
            platform_user_id='12345',
            platform_username='testuser',
            linked_at=timezone.now(),
        )
        self.assertEqual(conn.platform_username, 'testuser')
        self.assertEqual(str(conn), f'testuser ({self.user})')

    def test_create_twitter_connection(self):
        conn = TwitterConnection.objects.create(
            user=self.user,
            platform_user_id='67890',
            platform_username='twitteruser',
            linked_at=timezone.now(),
        )
        self.assertEqual(conn.platform_username, 'twitteruser')

    def test_create_discord_connection(self):
        conn = DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='11111',
            platform_username='discorduser',
            discriminator='1234',
            avatar_hash='abc123',
            linked_at=timezone.now(),
        )
        self.assertEqual(conn.platform_username, 'discorduser')
        self.assertEqual(conn.avatar_url, 'https://cdn.discordapp.com/avatars/11111/abc123.png')

    def test_discord_avatar_url_none_when_no_hash(self):
        conn = DiscordConnection.objects.create(
            user=self.user,
            platform_user_id='11111',
            platform_username='discorduser',
            linked_at=timezone.now(),
        )
        self.assertIsNone(conn.avatar_url)

    def test_one_to_one_constraint(self):
        GitHubConnection.objects.create(
            user=self.user,
            platform_user_id='12345',
            platform_username='testuser',
            linked_at=timezone.now(),
        )
        with self.assertRaises(IntegrityError):
            GitHubConnection.objects.create(
                user=self.user,
                platform_user_id='99999',
                platform_username='anotheruser',
                linked_at=timezone.now(),
            )

    def test_different_users_can_have_connections(self):
        GitHubConnection.objects.create(
            user=self.user,
            platform_user_id='12345',
            platform_username='user1',
            linked_at=timezone.now(),
        )
        GitHubConnection.objects.create(
            user=self.user2,
            platform_user_id='67890',
            platform_username='user2',
            linked_at=timezone.now(),
        )
        self.assertEqual(GitHubConnection.objects.count(), 2)

    def test_cascade_delete(self):
        GitHubConnection.objects.create(
            user=self.user,
            platform_user_id='12345',
            platform_username='testuser',
            linked_at=timezone.now(),
        )
        self.user.delete()
        self.assertEqual(GitHubConnection.objects.count(), 0)

    def test_access_via_related_name(self):
        GitHubConnection.objects.create(
            user=self.user,
            platform_user_id='12345',
            platform_username='testuser',
            linked_at=timezone.now(),
        )
        self.assertEqual(self.user.githubconnection.platform_username, 'testuser')


class UsedOAuthCodeTest(TestCase):
    def test_mark_used_new_code(self):
        result = UsedOAuthCode.mark_used('code123', 'github')
        self.assertTrue(result)

    def test_mark_used_duplicate_code(self):
        UsedOAuthCode.mark_used('code123', 'github')
        result = UsedOAuthCode.mark_used('code123', 'github')
        self.assertFalse(result)

    def test_same_code_different_platforms(self):
        result1 = UsedOAuthCode.mark_used('code123', 'github')
        result2 = UsedOAuthCode.mark_used('code123', 'twitter')
        self.assertTrue(result1)
        self.assertTrue(result2)

    def test_cleanup_old(self):
        UsedOAuthCode.objects.create(
            code='old_code',
            platform='github',
            used_at=timezone.now() - timedelta(minutes=15),
        )
        UsedOAuthCode.objects.create(
            code='new_code',
            platform='github',
        )
        deleted = UsedOAuthCode.cleanup_old(minutes=10)
        self.assertEqual(deleted, 1)
        self.assertEqual(UsedOAuthCode.objects.count(), 1)
        self.assertEqual(UsedOAuthCode.objects.first().code, 'new_code')
