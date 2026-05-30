from rest_framework import serializers

from .discord_roles import manual_refresh_next_allowed_at
from .models import GitHubConnection, TwitterConnection, DiscordConnection, DiscordRole


class GitHubConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubConnection
        fields = ['platform_username', 'linked_at']
        read_only_fields = ['platform_username', 'linked_at']


class PublicGitHubConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitHubConnection
        fields = ['platform_username']
        read_only_fields = fields


class TwitterConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TwitterConnection
        fields = ['platform_username', 'linked_at']
        read_only_fields = ['platform_username', 'linked_at']


class PublicTwitterConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TwitterConnection
        fields = ['platform_username']
        read_only_fields = fields


class DiscordRoleSerializer(serializers.ModelSerializer):
    color_hex = serializers.SerializerMethodField()

    def get_color_hex(self, obj):
        return obj.color_hex

    class Meta:
        model = DiscordRole
        fields = [
            'role_id', 'name', 'color', 'color_hex', 'position',
            'hoist', 'managed', 'mentionable',
        ]
        read_only_fields = fields


class DiscordConnectionSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    next_manual_role_sync_at = serializers.SerializerMethodField()
    mee6_xp = serializers.SerializerMethodField()
    mee6_level = serializers.SerializerMethodField()
    mee6_rank = serializers.SerializerMethodField()
    mee6_synced_at = serializers.SerializerMethodField()

    def _get_mee6_current_xp(self, obj):
        if hasattr(obj, '_mee6_current_xp_cache'):
            return obj._mee6_current_xp_cache

        from community_xp.models import Mee6CurrentXP
        from community_xp.services import get_default_guild_id

        current = (
            Mee6CurrentXP.objects
            .filter(
                guild_id=get_default_guild_id(),
                discord_id=obj.platform_user_id,
            )
            .first()
        )
        obj._mee6_current_xp_cache = current
        return current

    def get_avatar_url(self, obj):
        return obj.avatar_url

    def get_roles(self, obj):
        roles = obj.current_roles.filter(deleted_at__isnull=True).order_by('-position', 'name')
        return DiscordRoleSerializer(roles, many=True).data

    def get_next_manual_role_sync_at(self, obj):
        next_allowed_at = manual_refresh_next_allowed_at(obj)
        if next_allowed_at is None:
            return None
        return next_allowed_at

    def get_mee6_xp(self, obj):
        current = self._get_mee6_current_xp(obj)
        return current.xp if current else None

    def get_mee6_level(self, obj):
        current = self._get_mee6_current_xp(obj)
        return current.level if current else None

    def get_mee6_rank(self, obj):
        current = self._get_mee6_current_xp(obj)
        return current.rank if current else None

    def get_mee6_synced_at(self, obj):
        current = self._get_mee6_current_xp(obj)
        return current.synced_at if current else None

    class Meta:
        model = DiscordConnection
        fields = [
            'platform_username', 'linked_at', 'guild_member', 'guild_checked_at',
            'avatar_url', 'roles', 'roles_synced_at', 'roles_sync_error',
            'roles_manual_synced_at', 'next_manual_role_sync_at',
            'guild_joined_at', 'guild_nick',
            'mee6_xp', 'mee6_level', 'mee6_rank', 'mee6_synced_at',
        ]
        read_only_fields = fields


class PublicDiscordConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscordConnection
        fields = ['platform_username']
        read_only_fields = fields
