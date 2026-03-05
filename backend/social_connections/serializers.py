"""
Serializers for social connection models.
"""
from rest_framework import serializers
from social_connections.github.models import GitHubConnection
from social_connections.twitter.models import TwitterConnection
from social_connections.discord.models import DiscordConnection


class GitHubConnectionSerializer(serializers.ModelSerializer):
    """Serializer for GitHub connection data."""

    class Meta:
        model = GitHubConnection
        fields = ['username', 'linked_at']
        read_only_fields = ['username', 'linked_at']


class TwitterConnectionSerializer(serializers.ModelSerializer):
    """Serializer for Twitter connection data."""

    class Meta:
        model = TwitterConnection
        fields = ['username', 'linked_at']
        read_only_fields = ['username', 'linked_at']


class DiscordConnectionSerializer(serializers.ModelSerializer):
    """Serializer for Discord connection data."""
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = DiscordConnection
        fields = ['username', 'discriminator', 'avatar_url', 'linked_at']
        read_only_fields = ['username', 'discriminator', 'avatar_url', 'linked_at']

    def get_avatar_url(self, obj):
        return obj.avatar_url
