"""
Tests for social connection models.
"""
from django.test import TestCase
from django.utils import timezone
from users.models import User
from social_connections.github.models import GitHubConnection
from social_connections.twitter.models import TwitterConnection
from social_connections.discord.models import DiscordConnection


class GitHubConnectionModelTest(TestCase):
    """Tests for GitHubConnection model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890'
        )

    def test_create_github_connection(self):
        """Test creating a GitHub connection."""
        connection = GitHubConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='12345',
            access_token='encrypted_token',
            linked_at=timezone.now()
        )

        self.assertEqual(connection.user, self.user)
        self.assertEqual(connection.username, 'testuser')
        self.assertEqual(connection.platform_user_id, '12345')
        self.assertIsNotNone(connection.linked_at)

    def test_github_connection_str(self):
        """Test string representation of GitHub connection."""
        connection = GitHubConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='12345'
        )

        self.assertIn('testuser', str(connection))

    def test_one_to_one_relationship(self):
        """Test that user can only have one GitHub connection."""
        GitHubConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='12345'
        )

        # Creating another connection for the same user should fail
        with self.assertRaises(Exception):
            GitHubConnection.objects.create(
                user=self.user,
                username='anotheruser',
                platform_user_id='67890'
            )

    def test_access_via_user(self):
        """Test accessing GitHub connection via user.github_connection."""
        connection = GitHubConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='12345'
        )

        self.assertEqual(self.user.github_connection, connection)


class TwitterConnectionModelTest(TestCase):
    """Tests for TwitterConnection model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890'
        )

    def test_create_twitter_connection(self):
        """Test creating a Twitter connection."""
        connection = TwitterConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='12345',
            access_token='encrypted_token',
            refresh_token='encrypted_refresh_token',
            linked_at=timezone.now()
        )

        self.assertEqual(connection.user, self.user)
        self.assertEqual(connection.username, 'testuser')
        self.assertEqual(connection.platform_user_id, '12345')
        self.assertIsNotNone(connection.refresh_token)

    def test_access_via_user(self):
        """Test accessing Twitter connection via user.twitter_connection."""
        connection = TwitterConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='12345'
        )

        self.assertEqual(self.user.twitter_connection, connection)


class DiscordConnectionModelTest(TestCase):
    """Tests for DiscordConnection model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890'
        )

    def test_create_discord_connection(self):
        """Test creating a Discord connection."""
        connection = DiscordConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='12345',
            discriminator='1234',
            avatar_hash='abc123',
            access_token='encrypted_token',
            linked_at=timezone.now()
        )

        self.assertEqual(connection.user, self.user)
        self.assertEqual(connection.username, 'testuser')
        self.assertEqual(connection.discriminator, '1234')
        self.assertEqual(connection.avatar_hash, 'abc123')

    def test_avatar_url_property(self):
        """Test the avatar_url property."""
        connection = DiscordConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='123456789',
            avatar_hash='abc123def456'
        )

        expected_url = 'https://cdn.discordapp.com/avatars/123456789/abc123def456.png'
        self.assertEqual(connection.avatar_url, expected_url)

    def test_avatar_url_none_when_no_hash(self):
        """Test avatar_url returns None when no avatar hash."""
        connection = DiscordConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='12345',
            avatar_hash=''
        )

        self.assertIsNone(connection.avatar_url)

    def test_access_via_user(self):
        """Test accessing Discord connection via user.discord_connection."""
        connection = DiscordConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='12345'
        )

        self.assertEqual(self.user.discord_connection, connection)
