from django.contrib import admin

from .models import (
    DiscordConnection,
    DiscordEarnedRoleAssignment,
    DiscordRole,
    DiscordRoleSyncLock,
    GitHubConnection,
    PendingOAuthState,
    TwitterConnection,
    UsedOAuthCode,
)


class GitHubConnectionInline(admin.TabularInline):
    model = GitHubConnection
    extra = 0
    readonly_fields = ('platform_user_id', 'platform_username', 'linked_at', 'created_at')
    fields = ('platform_username', 'platform_user_id', 'linked_at', 'created_at')


class TwitterConnectionInline(admin.TabularInline):
    model = TwitterConnection
    extra = 0
    readonly_fields = ('platform_user_id', 'platform_username', 'linked_at', 'created_at')
    fields = ('platform_username', 'platform_user_id', 'linked_at', 'created_at')


class DiscordConnectionInline(admin.TabularInline):
    model = DiscordConnection
    extra = 0
    readonly_fields = (
        'platform_user_id',
        'platform_username',
        'linked_at',
        'guild_member',
        'guild_checked_at',
        'roles_synced_at',
        'created_at',
    )
    fields = (
        'platform_username',
        'platform_user_id',
        'linked_at',
        'guild_member',
        'guild_checked_at',
        'roles_synced_at',
        'created_at',
    )


@admin.register(GitHubConnection)
class GitHubConnectionAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform_username', 'platform_user_id', 'linked_at')
    search_fields = ('user__email', 'platform_username')
    readonly_fields = ('platform_user_id', 'access_token', 'linked_at', 'created_at', 'updated_at')


@admin.register(TwitterConnection)
class TwitterConnectionAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform_username', 'platform_user_id', 'linked_at')
    search_fields = ('user__email', 'platform_username')
    readonly_fields = ('platform_user_id', 'access_token', 'refresh_token', 'linked_at', 'created_at', 'updated_at')


@admin.register(DiscordConnection)
class DiscordConnectionAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'platform_username',
        'platform_user_id',
        'linked_at',
        'guild_member',
        'roles_synced_at',
    )
    search_fields = ('user__email', 'platform_username')
    readonly_fields = ('platform_user_id', 'access_token', 'refresh_token', 'linked_at',
                       'guild_member', 'guild_checked_at', 'roles_synced_at',
                       'roles_sync_error', 'roles_manual_synced_at', 'guild_joined_at',
                       'guild_nick', 'avatar_hash', 'created_at', 'updated_at')
    filter_horizontal = ('current_roles',)


@admin.register(DiscordRole)
class DiscordRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'guild_id', 'role_id', 'position', 'managed', 'deleted_at', 'last_synced_at')
    list_filter = ('guild_id', 'managed', 'deleted_at')
    search_fields = ('name', 'role_id', 'guild_id')
    readonly_fields = ('created_at', 'updated_at', 'last_synced_at')


@admin.register(DiscordRoleSyncLock)
class DiscordRoleSyncLockAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner_token', 'acquired_at', 'heartbeat_at', 'released_at')
    readonly_fields = ('name', 'owner_token', 'acquired_at', 'heartbeat_at', 'released_at')


@admin.register(DiscordEarnedRoleAssignment)
class DiscordEarnedRoleAssignmentAdmin(admin.ModelAdmin):
    list_select_related = ('connection__user',)
    list_display = ('created_at', 'role_name', 'discord_username', 'connection', 'total_points', 'poap_count')
    list_filter = ('role_name',)
    search_fields = ('discord_username', 'discord_user_id', 'connection__user__email')
    date_hierarchy = 'created_at'
    readonly_fields = (
        'connection',
        'discord_user_id',
        'discord_username',
        'role_id',
        'role_name',
        'total_points',
        'poap_count',
        'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PendingOAuthState)
class PendingOAuthStateAdmin(admin.ModelAdmin):
    list_display = ('platform', 'user', 'created_at', 'consumed_at')
    list_filter = ('platform',)
    readonly_fields = (
        'state_id',
        'platform',
        'user',
        'code_verifier',
        'redirect_url',
        'created_at',
        'consumed_at',
    )


@admin.register(UsedOAuthCode)
class UsedOAuthCodeAdmin(admin.ModelAdmin):
    list_display = ('platform', 'used_at')
    list_filter = ('platform',)
    readonly_fields = ('code', 'platform', 'used_at')
