from django.contrib import admin

from notifications import services as notification_services
from notifications.admin_mixins import BroadcastNotificationAdminMixin
from utils.admin_mixins import CloudinaryUploadMixin

from .models import Stream, StreamCategory


@admin.register(StreamCategory)
class StreamCategoryAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'group',
        'display_order',
        'is_active',
        'updated_at',
    )
    list_editable = ('group', 'display_order', 'is_active')
    list_filter = ('group', 'is_active')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'group', 'description', 'is_active'),
        }),
        ('Ordering', {
            'fields': ('display_order',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )


@admin.register(Stream)
class StreamAdmin(BroadcastNotificationAdminMixin, CloudinaryUploadMixin, admin.ModelAdmin):
    broadcast_event_slug = 'stream.published'
    broadcast_service = staticmethod(notification_services.broadcast_stream)
    broadcast_eligible = staticmethod(lambda obj: obj.is_active)
    broadcast_ineligible_reason = 'the stream is inactive'
    cloudinary_upload_fields = {
        'image_url': {
            'public_id_field': 'image_public_id',
            'folder': 'tally/gen-tv',
        },
    }

    list_display = (
        'title',
        'category',
        'detailed_category',
        'computed_status',
        'starts_at',
        'ends_at',
        'is_active',
    )
    list_editable = ('category', 'detailed_category', 'is_active')
    list_filter = ('category', 'detailed_category', 'is_active')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'starts_at'
    readonly_fields = ('created_at', 'updated_at', 'image_public_id')
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'description', 'is_active'),
        }),
        ('Channel & Schedule', {
            'fields': ('category', 'detailed_category', 'starts_at', 'ends_at'),
        }),
        ('Media', {
            'fields': ('url', 'image_url'),
            'description': 'Upload a cover image directly or paste a Cloudinary URL.',
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Status')
    def computed_status(self, obj):
        return obj.status
