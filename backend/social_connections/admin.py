from django.contrib import admin

from .models import GitHubConnection, TwitterConnection, DiscordConnection, UsedOAuthCode


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
    readonly_fields = ('platform_user_id', 'platform_username', 'linked_at', 'guild_member', 'guild_checked_at', 'created_at')
    fields = ('platform_username', 'platform_user_id', 'linked_at', 'guild_member', 'guild_checked_at', 'created_at')


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
    list_display = ('user', 'platform_username', 'platform_user_id', 'linked_at', 'guild_member')
    search_fields = ('user__email', 'platform_username')
    readonly_fields = ('platform_user_id', 'access_token', 'refresh_token', 'linked_at',
                       'guild_member', 'guild_checked_at', 'avatar_hash', 'created_at', 'updated_at')


@admin.register(UsedOAuthCode)
class UsedOAuthCodeAdmin(admin.ModelAdmin):
    list_display = ('platform', 'used_at')
    list_filter = ('platform',)
    readonly_fields = ('code', 'platform', 'used_at')
