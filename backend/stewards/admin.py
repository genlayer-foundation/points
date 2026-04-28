from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import (
    ReviewTemplate,
    Steward,
    StewardAssignment,
    WorkingGroup,
    WorkingGroupParticipant,
)


class StewardInline(admin.StackedInline):
    """Inline admin for Steward model to be used in UserAdmin"""
    model = Steward
    extra = 0  # Don't show empty rows
    max_num = 1  # Only one steward per user
    fields = ()  # No fields yet, model is empty
    verbose_name = "Steward Information"
    verbose_name_plural = "Steward Information"
    can_delete = True  # Allow deletion through inline


class StewardAssignmentForm(forms.ModelForm):
    class Meta:
        model = StewardAssignment
        fields = ('role', 'scope_category', 'scope_type')

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('scope_category') and cleaned.get('scope_type'):
            raise ValidationError(
                "An assignment may target a category OR a contribution type, not both. "
                "Leave both blank for a global assignment."
            )
        return cleaned


class StewardAssignmentInline(admin.TabularInline):
    """Inline for managing steward assignments from the steward detail page."""
    model = StewardAssignment
    form = StewardAssignmentForm
    extra = 1
    autocomplete_fields = ('scope_category', 'scope_type')
    fields = ('role', 'scope_category', 'scope_type')


@admin.register(Steward)
class StewardAdmin(admin.ModelAdmin):
    list_display = ('user', 'assignment_count', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__name')
    list_filter = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    inlines = [StewardAssignmentInline]

    fieldsets = (
        (None, {
            'fields': ('user',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def assignment_count(self, obj):
        return obj.assignments.count()
    assignment_count.short_description = 'Assignments'


@admin.register(StewardAssignment)
class StewardAssignmentAdmin(admin.ModelAdmin):
    form = StewardAssignmentForm
    list_display = ('steward', 'role', 'scope_category', 'scope_type', 'created_at')
    list_filter = ('role', 'scope_category', 'scope_type__category')
    search_fields = (
        'steward__user__name',
        'steward__user__email',
        'scope_category__name',
        'scope_type__name',
    )
    autocomplete_fields = ('steward', 'scope_category', 'scope_type')
    ordering = ('steward', 'role')


@admin.register(ReviewTemplate)
class ReviewTemplateAdmin(admin.ModelAdmin):
    list_display = ('action', 'label', 'text_preview', 'created_at', 'updated_at')
    list_filter = ('action',)
    search_fields = ('label', 'text')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('action', 'label')

    def text_preview(self, obj):
        return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text
    text_preview.short_description = 'Text Preview'


# Note: StewardInline is imported and added to UserAdmin in users/admin.py


class WorkingGroupParticipantInline(admin.TabularInline):
    """Inline admin for participants within a WorkingGroup"""
    model = WorkingGroupParticipant
    extra = 0
    autocomplete_fields = ['user']
    readonly_fields = ('created_at',)


@admin.register(WorkingGroup)
class WorkingGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'description', 'participant_count', 'discord_url', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)
    ordering = ('name',)
    inlines = [WorkingGroupParticipantInline]

    def participant_count(self, obj):
        return obj.participants.count()
    participant_count.short_description = 'Participants'


@admin.register(WorkingGroupParticipant)
class WorkingGroupParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'working_group', 'created_at')
    search_fields = ('user__name', 'user__email', 'user__address', 'working_group__name')
    list_filter = ('working_group', 'created_at')
    autocomplete_fields = ['user', 'working_group']
    ordering = ('-created_at',)
