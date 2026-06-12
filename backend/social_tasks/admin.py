from django import forms
from django.contrib import admin
from django.db.models import Count

from notifications import services as notification_services
from notifications.admin_mixins import BroadcastNotificationAdminMixin

from .models import SocialTask, SocialTaskCompletion
from .verifiers import get_choices

# All target_* model fields, picked up automatically so a new verifier's
# target field shows up on the admin form the moment it is added to the
# model. If a required field were missing from the form, SocialTask.clean()
# would raise a ValidationError keyed to it and crash the admin form
# rendering with a ValueError.
TARGET_FIELDS = tuple(
    f.name for f in SocialTask._meta.local_fields if f.name.startswith('target_')
)


@admin.register(SocialTask)
class SocialTaskAdmin(BroadcastNotificationAdminMixin, admin.ModelAdmin):
    # Broadcast goes only to the role the task's category targets
    # (builders/validators/community members), resolved in the service.
    broadcast_service = staticmethod(notification_services.broadcast_social_task)
    broadcast_eligible = staticmethod(lambda obj: obj.is_currently_active())
    broadcast_ineligible_reason = 'the task is inactive or outside its active window'
    list_display = (
        'name',
        'slug',
        'category',
        'platform',
        'verification_type',
        'points',
        'completions',
        'is_active',
        'starts_at',
        'ends_at',
        'order',
    )
    list_editable = ('is_active', 'order')
    list_filter = ('is_active', 'category', 'platform', 'verification_type')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('platform',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            completion_count=Count('completions')
        )

    @admin.display(ordering='completion_count', description='Completions')
    def completions(self, obj):
        return obj.completion_count
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'category', 'points', 'order'),
        }),
        ('Action', {
            'fields': ('action_url', 'cta_text'),
            'description': (
                'action_url is where the user is sent on click. platform is derived '
                'automatically from the chosen verification logic.'
            ),
        }),
        ('Verification logic', {
            'fields': ('verification_type', 'platform'),
            'description': (
                'Verification logic determines how completion is checked. The dropdown '
                'is auto-populated from the verifier registry — add a new file under '
                'social_tasks/verifiers/ and it shows up here.'
            ),
        }),
        ('Verification targets', {
            'fields': TARGET_FIELDS,
            'description': (
                'Each verification logic requires only the field(s) it needs; others '
                'are ignored. See the help text on each field.'
            ),
        }),
        ('Lifecycle', {
            'fields': ('is_active', 'starts_at', 'ends_at'),
        }),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'verification_type':
            choices = [('', '----')] + list(get_choices())
            kwargs['widget'] = forms.Select(choices=choices)
            field = super().formfield_for_dbfield(db_field, request, **kwargs)
            # Re-apply choices on the form field itself (widget alone is not enough
            # for validation).
            field.choices = choices
            return field
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(SocialTaskCompletion)
class SocialTaskCompletionAdmin(admin.ModelAdmin):
    list_display = ('user', 'task', 'points_awarded', 'verification_type', 'completed_at')
    list_filter = ('verification_type', 'task')
    search_fields = ('user__email', 'user__name', 'task__name', 'task__slug')
    readonly_fields = (
        'user',
        'task',
        'points_awarded',
        'completed_at',
        'verification_type',
        'verification_data',
    )

    def has_add_permission(self, request):
        # Completions are only created through the API's verification flow;
        # every field is readonly so the add form could never produce a valid
        # row anyway.
        return False
