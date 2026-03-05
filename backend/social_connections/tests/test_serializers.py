"""
Tests for social connection serializers.
"""
from django.test import TestCase
from django.utils import timezone
from users.models import User
from users.serializers import UserSerializer
from social_connections.github.models import GitHubConnection
from social_connections.twitter.models import TwitterConnection
from social_connections.discord.models import DiscordConnection
from social_connections.serializers import (
    GitHubConnectionSerializer,
    TwitterConnectionSerializer,
    DiscordConnectionSerializer
)


class GitHubConnectionSerializerTest(TestCase):
    """Tests for GitHubConnectionSerializer."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890'
        )
        self.connection = GitHubConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='12345',
            linked_at=timezone.now()
        )

    def test_serializer_fields(self):
        """Test that serializer returns expected fields."""
        serializer = GitHubConnectionSerializer(self.connection)
        data = serializer.data

        self.assertIn('username', data)
        self.assertIn('linked_at', data)
        self.assertEqual(data['username'], 'testuser')

    def test_serializer_excludes_sensitive_fields(self):
        """Test that sensitive fields are not exposed."""
        serializer = GitHubConnectionSerializer(self.connection)
        data = serializer.data

        self.assertNotIn('access_token', data)
        self.assertNotIn('platform_user_id', data)


class TwitterConnectionSerializerTest(TestCase):
    """Tests for TwitterConnectionSerializer."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890'
        )
        self.connection = TwitterConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='12345',
            linked_at=timezone.now()
        )

    def test_serializer_fields(self):
        """Test that serializer returns expected fields."""
        serializer = TwitterConnectionSerializer(self.connection)
        data = serializer.data

        self.assertIn('username', data)
        self.assertIn('linked_at', data)
        self.assertEqual(data['username'], 'testuser')


class DiscordConnectionSerializerTest(TestCase):
    """Tests for DiscordConnectionSerializer."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890'
        )
        self.connection = DiscordConnection.objects.create(
            user=self.user,
            username='testuser',
            platform_user_id='123456789',
            discriminator='1234',
            avatar_hash='abc123',
            linked_at=timezone.now()
        )

    def test_serializer_fields(self):
        """Test that serializer returns expected fields."""
        serializer = DiscordConnectionSerializer(self.connection)
        data = serializer.data

        self.assertIn('username', data)
        self.assertIn('discriminator', data)
        self.assertIn('avatar_url', data)
        self.assertIn('linked_at', data)

    def test_avatar_url_included(self):
        """Test that avatar_url is correctly computed."""
        serializer = DiscordConnectionSerializer(self.connection)
        data = serializer.data

        expected_url = 'https://cdn.discordapp.com/avatars/123456789/abc123.png'
        self.assertEqual(data['avatar_url'], expected_url)


class UserSerializerSocialConnectionsTest(TestCase):
    """Tests for UserSerializer with social connections."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234567890123456789012345678901234567890',
            name='Test User'
        )

    def test_user_without_connections(self):
        """Test UserSerializer when user has no social connections."""
        serializer = UserSerializer(self.user)
        data = serializer.data

        self.assertIsNone(data['github_connection'])
        self.assertIsNone(data['twitter_connection'])
        self.assertIsNone(data['discord_connection'])
        self.assertEqual(data['github_username'], '')
        self.assertIsNone(data['github_linked_at'])

    def test_user_with_github_connection(self):
        """Test UserSerializer includes GitHub connection data."""
        GitHubConnection.objects.create(
            user=self.user,
            username='githubuser',
            platform_user_id='12345',
            linked_at=timezone.now()
        )

        serializer = UserSerializer(self.user)
        data = serializer.data

        self.assertIsNotNone(data['github_connection'])
        self.assertEqual(data['github_connection']['username'], 'githubuser')
        # Legacy fields
        self.assertEqual(data['github_username'], 'githubuser')
        self.assertIsNotNone(data['github_linked_at'])

    def test_user_with_twitter_connection(self):
        """Test UserSerializer includes Twitter connection data."""
        TwitterConnection.objects.create(
            user=self.user,
            username='twitteruser',
            platform_user_id='12345',
            linked_at=timezone.now()
        )

        serializer = UserSerializer(self.user)
        data = serializer.data

        self.assertIsNotNone(data['twitter_connection'])
        self.assertEqual(data['twitter_connection']['username'], 'twitteruser')

    def test_user_with_discord_connection(self):
        """Test UserSerializer includes Discord connection data."""
        DiscordConnection.objects.create(
            user=self.user,
            username='discorduser',
            platform_user_id='12345',
            discriminator='1234',
            linked_at=timezone.now()
        )

        serializer = UserSerializer(self.user)
        data = serializer.data

        self.assertIsNotNone(data['discord_connection'])
        self.assertEqual(data['discord_connection']['username'], 'discorduser')
        self.assertEqual(data['discord_connection']['discriminator'], '1234')

    def test_user_with_all_connections(self):
        """Test UserSerializer with all social connections."""
        GitHubConnection.objects.create(
            user=self.user,
            username='githubuser',
            platform_user_id='111',
            linked_at=timezone.now()
        )
        TwitterConnection.objects.create(
            user=self.user,
            username='twitteruser',
            platform_user_id='222',
            linked_at=timezone.now()
        )
        DiscordConnection.objects.create(
            user=self.user,
            username='discorduser',
            platform_user_id='333',
            linked_at=timezone.now()
        )

        serializer = UserSerializer(self.user)
        data = serializer.data

        self.assertEqual(data['github_connection']['username'], 'githubuser')
        self.assertEqual(data['twitter_connection']['username'], 'twitteruser')
        self.assertEqual(data['discord_connection']['username'], 'discorduser')
