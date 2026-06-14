import logging

from django import forms
from django.contrib import admin, messages

from . import campaigns
from .models import CustomNotification, Notification, NotificationReceipt

logger = logging.getLogger(__name__)


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


class CustomNotificationAdminForm(forms.ModelForm):
    target_roles = forms.MultipleChoiceField(
        choices=CustomNotification.ROLE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='Roles mode only. Union: a user with any selected role receives it once.',
    )
    send_now = forms.BooleanField(
        required=False,
        label='Send now',
        help_text='Off by default. Saving stays a silent draft unless this is checked.',
    )
    recall_now = forms.BooleanField(
        required=False,
        label='Recall delivered portal notifications',
        help_text='Deletes delivered portal notification rows for this campaign; the campaign record stays for audit.',
    )

    class Meta:
        model = CustomNotification
        fields = [
            'title', 'body', 'link_url', 'link_label', 'priority',
            'target_mode', 'target_roles', 'target_users', 'target_wallets',
        ]
        widgets = {
            'target_mode': forms.RadioSelect,
            'target_wallets': forms.Textarea(attrs={'rows': 6}),
        }

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get('target_mode')

        if cleaned.get('link_label') and not cleaned.get('link_url'):
            self.add_error('link_label', 'A link label needs a link URL.')
        if cleaned.get('send_now') and cleaned.get('recall_now'):
            self.add_error('recall_now', 'Choose either send/resend or recall, not both.')

        if mode == CustomNotification.TARGET_ROLES and not cleaned.get('target_roles'):
            self.add_error('target_roles', 'Select at least one role.')
        if mode == CustomNotification.TARGET_USERS and not cleaned.get('target_users'):
            self.add_error('target_users', 'Pick at least one user.')
        if mode == CustomNotification.TARGET_WALLETS:
            addresses, invalid_lines = campaigns.parse_wallet_lines(cleaned.get('target_wallets', ''))
            if not addresses:
                detail = f" Invalid lines: {', '.join(invalid_lines[:5])}" if invalid_lines else ''
                self.add_error('target_wallets', f'Paste at least one valid wallet address.{detail}')

        # Keep stored targeting unambiguous: clear the fields that don't
        # belong to the chosen mode (the users M2M clears in save_related).
        if mode != CustomNotification.TARGET_ROLES:
            cleaned['target_roles'] = []
        if mode != CustomNotification.TARGET_WALLETS:
            cleaned['target_wallets'] = ''
        return cleaned


@admin.register(CustomNotification)
class CustomNotificationAdmin(admin.ModelAdmin):
    form = CustomNotificationAdminForm
    autocomplete_fields = ('target_users',)
    list_display = ('title', 'target_mode', 'status', 'sent_at', 'sent_count', 'created_at')
    list_filter = ('status', 'target_mode', 'priority')
    search_fields = ('title', 'body')
    readonly_fields = (
        'audience_preview', 'channels_display', 'status', 'sent_at', 'sent_by',
        'sent_count', 'unmatched_report', 'created_at', 'updated_at',
    )
    actions = ('send_selected', 'resend_selected', 'recall_selected')

    fieldsets = (
        ('Message', {
            'fields': ('title', 'body', 'link_url', 'link_label', 'priority'),
        }),
        ('Targeting', {
            'fields': ('target_mode', 'target_roles', 'target_users', 'target_wallets'),
            'description': 'Fill only the field that matches the chosen mode; the others are ignored.',
        }),
        ('Send', {
            'fields': ('send_now', 'recall_now', 'audience_preview', 'channels_display'),
        }),
        ('Delivery record', {
            'fields': ('status', 'sent_at', 'sent_by', 'sent_count', 'unmatched_report'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Audience preview')
    def audience_preview(self, obj):
        if not obj or not obj.pk:
            return 'Save as draft first to preview reach.'
        audience = campaigns.resolve_recipients(obj)
        preview = f'~{audience.users.count()} recipient(s)'
        if audience.unmatched_wallets:
            preview += f' · {len(audience.unmatched_wallets)} wallet line(s) unmatched'
        return preview

    @admin.display(description='Channels')
    def channels_display(self, obj):
        channels = obj.channels if obj and obj.pk else ['portal']
        return ', '.join(channels)

    @admin.display(description='Unmatched wallets')
    def unmatched_report(self, obj):
        if not obj or not obj.unmatched_wallets:
            return '—'
        return '\n'.join(obj.unmatched_wallets)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.status == CustomNotification.STATUS_SENT:
            form.base_fields['send_now'].label = (
                'Resend now (resurfaces as unread for the current audience)'
            )
        return form

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # The M2M is saved after this hook; the send happens in save_related.
        request._send_campaign_now = form.cleaned_data.get('send_now', False)
        request._recall_campaign_now = form.cleaned_data.get('recall_now', False)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        campaign = form.instance

        if campaign.target_mode != CustomNotification.TARGET_USERS:
            campaign.target_users.clear()

        if getattr(request, '_recall_campaign_now', False):
            self._recall_campaign(request, campaign)
        elif getattr(request, '_send_campaign_now', False):
            self._send_campaign(request, campaign)
        else:
            try:
                audience = campaigns.resolve_recipients(campaign)
                preview = f'Draft saved. Would currently reach ~{audience.users.count()} user(s).'
                if audience.unmatched_wallets:
                    preview += self._unmatched_summary(audience.unmatched_wallets)
                self.message_user(request, preview, level=messages.INFO)
            except Exception:
                logger.exception('Failed to preview campaign audience for %r', campaign)

    def _send_campaign(self, request, campaign):
        try:
            result = campaigns.send_campaign(campaign, actor=request.user)
        except campaigns.CampaignSendError as error:
            self.message_user(request, f'Not sent: {error} The draft was saved.', level=messages.WARNING)
            return
        except Exception:
            logger.exception('Failed to send campaign %r', campaign)
            self.message_user(
                request,
                'The campaign was saved, but sending failed; check server logs.',
                level=messages.ERROR,
            )
            return

        message = f'Sent to {result.total} user(s) ({result.created} new, {result.refreshed} resurfaced).'
        if result.unmatched_wallets:
            message += self._unmatched_summary(result.unmatched_wallets)
        self.message_user(
            request,
            message,
            level=messages.WARNING if result.unmatched_wallets else messages.SUCCESS,
        )

    def _recall_campaign(self, request, campaign):
        try:
            deleted = campaigns.recall_campaign(campaign)
        except Exception:
            logger.exception('Failed to recall campaign %r', campaign)
            self.message_user(
                request,
                'The campaign was saved, but delivered notifications could not be recalled; check server logs.',
                level=messages.ERROR,
            )
            return

        if deleted:
            self.message_user(
                request,
                f'Recalled {deleted} delivered portal notification(s). The campaign record was kept.',
                level=messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                'No delivered portal notifications were found for this campaign.',
                level=messages.INFO,
            )

    @staticmethod
    def _unmatched_summary(unmatched):
        shown = ', '.join(unmatched[:10])
        suffix = '...' if len(unmatched) > 10 else ''
        return f' {len(unmatched)} wallet line(s) unmatched: {shown}{suffix}'

    @admin.action(description='Send selected draft custom notifications')
    def send_selected(self, request, queryset):
        self._run_bulk(request, queryset.filter(status=CustomNotification.STATUS_DRAFT), queryset)

    @admin.action(description='Resend selected sent custom notifications')
    def resend_selected(self, request, queryset):
        self._run_bulk(request, queryset.filter(status=CustomNotification.STATUS_SENT), queryset)

    @admin.action(description='Recall delivered portal notifications for selected custom notifications')
    def recall_selected(self, request, queryset):
        campaigns_recalled = 0
        deleted = 0
        failed = 0

        for campaign in queryset:
            try:
                count = campaigns.recall_campaign(campaign)
            except Exception:
                logger.exception('Failed to recall campaign %r', campaign)
                failed += 1
                continue
            if count:
                campaigns_recalled += 1
                deleted += count

        message = (
            f'Recalled {deleted} delivered portal notification(s) '
            f'from {campaigns_recalled} custom notification(s).'
        )
        if failed:
            message += f' Failed {failed}; check server logs.'
        self.message_user(
            request,
            message,
            level=messages.WARNING if failed else messages.SUCCESS,
        )

    def _run_bulk(self, request, eligible, selected):
        sent = 0
        reached = 0
        failed = 0
        for campaign in eligible:
            try:
                result = campaigns.send_campaign(campaign, actor=request.user)
            except Exception:
                logger.exception('Failed to send campaign %r', campaign)
                failed += 1
                continue
            sent += 1
            reached += result.total

        skipped = selected.count() - eligible.count()
        message = f'Sent {sent} custom notification(s) reaching {reached} user(s).'
        if skipped:
            message += f' Skipped {skipped} with the wrong status.'
        if failed:
            message += f' Failed {failed}; check server logs.'
        self.message_user(
            request,
            message,
            level=messages.WARNING if (skipped or failed) else messages.SUCCESS,
        )
