from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from utils.admin_mixins import CloudinaryUploadMixin

from .models import Project


@admin.register(Project)
class ProjectAdmin(CloudinaryUploadMixin, admin.ModelAdmin):
    cloudinary_upload_fields = {
        'hero_image_url': {
            'public_id_field': 'hero_image_public_id',
            'folder': 'tally/projects',
        },
        'hero_image_url_tablet': {
            'public_id_field': 'hero_image_tablet_public_id',
            'folder': 'tally/projects',
        },
        'hero_image_url_mobile': {
            'public_id_field': 'hero_image_mobile_public_id',
            'folder': 'tally/projects',
        },
        'user_profile_image_url': {
            'public_id_field': 'user_profile_image_public_id',
            'folder': 'tally/projects/avatars',
        },
    }

    list_display = ('title', 'slug', 'user', 'status', 'show_in_overview', 'order', 'created_at')
    list_filter = ('status', 'show_in_overview', 'created_at')
    search_fields = ('title', 'slug', 'description', 'details', 'user__name', 'user__address')
    list_editable = ('order', 'status', 'show_in_overview')
    raw_id_fields = ('user',)
    autocomplete_fields = ('participants', 'related_contributions')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = (
        'created_at',
        'updated_at',
        'hero_image_public_id',
        'hero_image_tablet_public_id',
        'hero_image_mobile_public_id',
        'user_profile_image_public_id',
        'selected_participants',
        'selected_related_contributions',
    )
    ordering = ('order', '-created_at')

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'author', 'description', 'status', 'show_in_overview', 'order'),
        }),
        ('Relations', {
            'fields': (
                'user',
                'participants',
                'selected_participants',
                'related_contributions',
                'selected_related_contributions',
            ),
        }),
        ('Project Detail', {
            'fields': (
                'details',
                'view_url',
                'url',
                'github_url',
                'x_url',
                'telegram_url',
                'discord_url',
                'demo_url',
            ),
        }),
        ('Media', {
            'fields': (
                'hero_image_url',
                'hero_image_url_tablet',
                'hero_image_url_mobile',
                'user_profile_image_url',
            ),
            'description': 'Upload images directly or paste Cloudinary URLs. Tablet/mobile hero images are optional and fall back to the main hero image.',
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Selected participants')
    def selected_participants(self, obj):
        if not obj or not obj.pk:
            return 'Save the project before reviewing selected participants.'

        participants = obj.participants.order_by('name', 'email', 'id')
        if not participants.exists():
            return 'No participants selected.'

        rows = (
            (
                reverse('admin:users_user_change', args=[participant.pk]),
                participant.name or participant.email or participant.address or f'User {participant.pk}',
                participant.email or participant.address or '',
            )
            for participant in participants
        )
        return format_html(
            '<ul style="margin: 0; padding-left: 18px;">{}</ul>',
            format_html_join('', '<li><a href="{}">{}</a> <span style="color: #666;">{}</span></li>', rows),
        )

    @admin.display(description='Selected related contributions')
    def selected_related_contributions(self, obj):
        if not obj or not obj.pk:
            return 'Save the project before reviewing selected related contributions.'

        contributions = obj.related_contributions.select_related('user', 'contribution_type').order_by(
            'user__name',
            'user__email',
            '-contribution_date',
            '-created_at',
        )
        if not contributions.exists():
            return 'No related contributions selected.'

        rows = (
            (
                reverse('admin:contributions_contribution_change', args=[contribution.pk]),
                contribution.title or f'Contribution {contribution.pk}',
                contribution.user.name or contribution.user.email or contribution.user.address,
                contribution.contribution_type.name,
            )
            for contribution in contributions
        )
        return format_html(
            '<ul style="margin: 0; padding-left: 18px;">{}</ul>',
            format_html_join(
                '',
                '<li><a href="{}">{}</a> <span style="color: #666;">by {} - {}</span></li>',
                rows,
            ),
        )
