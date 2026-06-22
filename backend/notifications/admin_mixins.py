import logging

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.utils import flatten_fieldsets

from .services import estimate_broadcast_reach, recall_broadcast

logger = logging.getLogger(__name__)

BROADCAST_FORM_FIELDS = (
    'broadcast_notification',
    'recall_broadcast_notification',
    'notification_message',
)


class BroadcastNotificationAdminMixin:
    """Adds an explicit, off-by-default broadcast control to a ModelAdmin.

    Saving, editing, activating, or deactivating objects stays silent. A
    broadcast notification is only created when the admin checks
    "Broadcast notification now" on the change form or runs the bulk action.

    Configure on the concrete admin:
        broadcast_event_slug = 'partner.published'
        broadcast_service = staticmethod(services.broadcast_partner)
        broadcast_eligible = staticmethod(lambda obj: obj.is_active)
        broadcast_ineligible_reason = 'it is not active'
    """

    broadcast_event_slug = None
    broadcast_service = None
    broadcast_eligible = staticmethod(lambda obj: True)
    broadcast_ineligible_reason = 'it is not active'

    def get_form(self, request, obj=None, **kwargs):
        # The admin passes fields flattened from get_fieldsets(), which include
        # our extra form-only fields; strip them before the model form factory
        # runs, then declare them on the returned form class.
        fields = kwargs.get('fields')
        if fields:
            kwargs['fields'] = [field for field in fields if field not in BROADCAST_FORM_FIELDS]

        base_form = super().get_form(request, obj, **kwargs)

        class BroadcastNotificationForm(base_form):
            broadcast_notification = forms.BooleanField(
                required=False,
                label='Broadcast notification now',
                help_text='Off by default. Saving stays silent unless this is checked.',
            )
            recall_broadcast_notification = forms.BooleanField(
                required=False,
                label='Recall existing broadcast notification',
                help_text='Deletes the existing broadcast row for this item, if any.',
            )
            notification_message = forms.CharField(
                required=False,
                label='Notification message',
                widget=forms.Textarea(attrs={'rows': 2}),
                help_text='Optional. Falls back to the default copy for this item.',
            )

            def clean(self):
                cleaned_data = super().clean()
                if (
                    cleaned_data.get('broadcast_notification')
                    and cleaned_data.get('recall_broadcast_notification')
                ):
                    raise forms.ValidationError('Choose either broadcast or recall, not both.')
                return cleaned_data

        for field_name, field in base_form.base_fields.items():
            if field_name in BroadcastNotificationForm.base_fields:
                BroadcastNotificationForm.base_fields[field_name] = field

        return BroadcastNotificationForm

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        if 'broadcast_notification' in flatten_fieldsets(fieldsets):
            return fieldsets
        fieldsets.append((
            'Notification',
            {
                'fields': BROADCAST_FORM_FIELDS,
                'description': (
                    'Optional broadcast. Creating, editing, activating, or '
                    'deactivating stays silent unless this is checked. '
                    'Re-broadcasting the same item resurfaces it as unread '
                    'instead of duplicating it. Recall removes the existing '
                    'broadcast from user feeds.'
                ),
            },
        ))
        return fieldsets

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'broadcast_selected_notifications' not in actions:
            action = self.get_action('broadcast_selected_notifications')
            if action:
                actions['broadcast_selected_notifications'] = action
        if 'recall_selected_notifications' not in actions:
            action = self.get_action('recall_selected_notifications')
            if action:
                actions['recall_selected_notifications'] = action
        return actions

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if form.cleaned_data.get('recall_broadcast_notification'):
            self._recall_broadcast(request, obj)
            return
        if not form.cleaned_data.get('broadcast_notification'):
            return
        if not self.broadcast_eligible(obj):
            self.message_user(
                request,
                f'Notification was not broadcast because {self.broadcast_ineligible_reason}.',
                level=messages.WARNING,
            )
            return
        self._send_broadcast(request, obj, form.cleaned_data.get('notification_message', ''))

    @admin.action(description='Broadcast notification for selected items')
    def broadcast_selected_notifications(self, request, queryset):
        sent = 0
        skipped = 0
        failed = 0
        last_audience = None
        for obj in queryset:
            if not self.broadcast_eligible(obj):
                skipped += 1
                continue
            try:
                notification = self.broadcast_service(obj, actor=request.user)
            except Exception:
                logger.exception('Failed to broadcast notification for %r', obj)
                failed += 1
                continue
            last_audience = notification.audience
            sent += 1

        if sent:
            reach = estimate_broadcast_reach(last_audience)
            message = f'Published {sent} broadcast notification(s) reaching ~{reach} users.'
        else:
            message = 'No broadcast notifications were published.'
        if skipped:
            message += f' Skipped {skipped} item(s) because {self.broadcast_ineligible_reason}.'
        if failed:
            message += f' Failed to broadcast {failed} item(s); check server logs.'
        self.message_user(
            request,
            message,
            level=messages.WARNING if (skipped or failed) else messages.SUCCESS,
        )

    @admin.action(description='Recall broadcast notification for selected items')
    def recall_selected_notifications(self, request, queryset):
        recalled = 0
        missing = 0
        failed = 0

        for obj in queryset:
            try:
                deleted = self._recall_broadcast_count(obj)
            except Exception:
                logger.exception('Failed to recall broadcast notification for %r', obj)
                failed += 1
                continue
            if deleted:
                recalled += deleted
            else:
                missing += 1

        message = f'Recalled {recalled} broadcast notification(s).'
        if missing:
            message += f' No existing broadcast found for {missing} item(s).'
        if failed:
            message += f' Failed to recall {failed}; check server logs.'
        self.message_user(
            request,
            message,
            level=messages.WARNING if (missing or failed) else messages.SUCCESS,
        )

    def _send_broadcast(self, request, obj, message=''):
        # The object is already saved at this point; a broadcast failure must
        # not turn the admin save into a server error.
        try:
            notification = self.broadcast_service(obj, actor=request.user, message=message)
        except Exception:
            logger.exception('Failed to broadcast notification for %r', obj)
            self.message_user(
                request,
                'The item was saved, but the broadcast notification failed to publish; check server logs.',
                level=messages.ERROR,
            )
            return
        reach = estimate_broadcast_reach(notification.audience)
        self.message_user(
            request,
            f'Broadcast notification published, reaching ~{reach} users.',
            level=messages.SUCCESS,
        )

    def _recall_broadcast_count(self, obj):
        if not self.broadcast_event_slug:
            raise RuntimeError(
                f'{self.__class__.__name__} must set broadcast_event_slug to recall notifications.'
            )
        return recall_broadcast(self.broadcast_event_slug, obj)

    def _recall_broadcast(self, request, obj):
        try:
            deleted = self._recall_broadcast_count(obj)
        except Exception:
            logger.exception('Failed to recall broadcast notification for %r', obj)
            self.message_user(
                request,
                'The item was saved, but the broadcast notification could not be recalled; check server logs.',
                level=messages.ERROR,
            )
            return

        if deleted:
            self.message_user(
                request,
                'Broadcast notification recalled from user feeds.',
                level=messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                'No existing broadcast notification was found for this item.',
                level=messages.INFO,
            )
