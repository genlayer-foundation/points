from django.contrib import admin

from notifications import services as notification_services
from notifications.admin_mixins import BroadcastNotificationAdminMixin

from .models import TargetNodeVersion


@admin.register(TargetNodeVersion)
class TargetNodeVersionAdmin(BroadcastNotificationAdminMixin, admin.ModelAdmin):
    # Broadcasts go to the validators audience only (see notifications/registry.py).
    broadcast_event_slug = 'node_version.published'
    broadcast_service = staticmethod(notification_services.broadcast_target_node_version)
    broadcast_eligible = staticmethod(lambda obj: obj.is_active)
    broadcast_ineligible_reason = 'the target node version is inactive'

    list_display = ('version', 'network', 'target_date', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'network', 'target_date')
    search_fields = ('version',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('version', 'network', 'target_date', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """
        Make certain fields readonly after creation.
        """
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:  # If editing existing object
            # Optionally make version readonly after creation
            # readonly_fields = readonly_fields + ('version',)
            pass
        return readonly_fields
