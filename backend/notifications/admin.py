from django.contrib import admin

from .models import Notification, NotificationReceipt


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'recipient',
        'audience',
        'category',
        'event_type',
        'priority',
        'read_at',
        'created_at',
    )
    list_filter = ('category', 'event_type', 'priority', 'audience')
    search_fields = ('title', 'body', 'recipient__email', 'recipient__address', 'recipient__name')
    raw_id_fields = ('recipient', 'actor')
    readonly_fields = (
        'created_at',
        'updated_at',
        'read_at',
        'dedupe_key',
        'source_app',
        'source_model',
        'source_object_id',
        'payload',
    )
    ordering = ('-created_at',)


@admin.register(NotificationReceipt)
class NotificationReceiptAdmin(admin.ModelAdmin):
    list_display = ('notification', 'user', 'read_at', 'created_at')
    search_fields = ('notification__title', 'user__email', 'user__address')
    raw_id_fields = ('notification', 'user')
    readonly_fields = ('created_at', 'updated_at')
