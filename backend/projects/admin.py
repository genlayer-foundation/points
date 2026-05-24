from django.contrib import admin

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

    list_display = ('title', 'slug', 'user', 'status', 'order', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'slug', 'description', 'details', 'user__name', 'user__address')
    list_editable = ('order', 'status')
    raw_id_fields = ('user',)
    filter_horizontal = ('participants', 'related_contributions')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = (
        'created_at',
        'updated_at',
        'hero_image_public_id',
        'hero_image_tablet_public_id',
        'hero_image_mobile_public_id',
        'user_profile_image_public_id',
    )
    ordering = ('order', '-created_at')

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'author', 'description', 'status', 'order'),
        }),
        ('Relations', {
            'fields': ('user', 'participants', 'related_contributions'),
        }),
        ('Project Detail', {
            'fields': (
                'details',
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
