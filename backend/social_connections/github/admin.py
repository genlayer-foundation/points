from django.contrib import admin
from .models import GitHubConnection


@admin.register(GitHubConnection)
class GitHubConnectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'username', 'platform_user_id', 'linked_at', 'created_at']
    list_filter = ['linked_at']
    search_fields = ['user__email', 'user__name', 'username', 'platform_user_id']
    readonly_fields = ['platform_user_id', 'access_token', 'linked_at', 'created_at', 'updated_at']
    raw_id_fields = ['user']

    fieldsets = (
        (None, {
            'fields': ('user', 'username', 'platform_user_id')
        }),
        ('Timestamps', {
            'fields': ('linked_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
