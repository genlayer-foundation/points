from rest_framework import serializers

from .models import GitHubConnection, TwitterConnection, DiscordConnection


class GitHubConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubConnection
        fields = ['platform_username', 'linked_at']
        read_only_fields = ['platform_username', 'linked_at']


class TwitterConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TwitterConnection
        fields = ['platform_username', 'linked_at']
        read_only_fields = ['platform_username', 'linked_at']


class DiscordConnectionSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    def get_avatar_url(self, obj):
        return obj.avatar_url

    class Meta:
        model = DiscordConnection
        fields = ['platform_username', 'linked_at', 'guild_member', 'guild_checked_at', 'avatar_url']
        read_only_fields = ['platform_username', 'linked_at', 'guild_member', 'guild_checked_at', 'avatar_url']
