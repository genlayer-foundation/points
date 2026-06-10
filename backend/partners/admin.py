from django.contrib import admin

from notifications import services as notification_services
from notifications.admin_mixins import BroadcastNotificationAdminMixin
from utils.admin_mixins import CloudinaryUploadMixin

from .models import Partner


@admin.register(Partner)
class PartnerAdmin(BroadcastNotificationAdminMixin, CloudinaryUploadMixin, admin.ModelAdmin):
    broadcast_service = staticmethod(notification_services.broadcast_partner)
    broadcast_eligible = staticmethod(lambda obj: obj.is_active)
    broadcast_ineligible_reason = 'the partner is inactive'

    cloudinary_upload_fields = {
        'logo_url': {
            'public_id_field': 'logo_public_id',
            'folder': 'tally/partners',
        },
    }

    list_display = (
        'name',
        'display_order',
        'is_active',
        'website_url',
        'created_at',
    )
    list_editable = ('display_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at', 'logo_public_id')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'is_active'),
        }),
        ('URLs', {
            'fields': ('logo_url', 'website_url', 'url'),
            'description': 'Upload a logo directly or paste a Cloudinary URL.',
        }),
        ('Display', {
            'fields': ('display_order',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
