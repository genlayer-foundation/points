from django.contrib import admin
from .models import DiscordConnection


@admin.register(DiscordConnection)
class DiscordConnectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'username', 'discriminator', 'platform_user_id', 'linked_at', 'created_at']
    list_filter = ['linked_at']
    search_fields = ['user__email', 'user__name', 'username', 'platform_user_id']
    readonly_fields = ['platform_user_id', 'access_token', 'refresh_token', 'avatar_hash', 'linked_at', 'created_at', 'updated_at']
    raw_id_fields = ['user']

    fieldsets = (
        (None, {
            'fields': ('user', 'username', 'discriminator', 'platform_user_id')
        }),
        ('Avatar', {
            'fields': ('avatar_hash',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('linked_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
