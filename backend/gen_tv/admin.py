from django.contrib import admin

from utils.admin_mixins import CloudinaryUploadMixin

from .models import Stream


@admin.register(Stream)
class StreamAdmin(CloudinaryUploadMixin, admin.ModelAdmin):
    cloudinary_upload_fields = {
        'image_url': {
            'public_id_field': 'image_public_id',
            'folder': 'tally/gen-tv',
        },
    }

    list_display = (
        'title',
        'category',
        'computed_status',
        'starts_at',
        'ends_at',
        'is_active',
    )
    list_editable = ('is_active',)
    list_filter = ('category', 'is_active')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'starts_at'
    readonly_fields = ('created_at', 'updated_at', 'image_public_id')
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'description', 'is_active'),
        }),
        ('Channel & Schedule', {
            'fields': ('category', 'starts_at', 'ends_at'),
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
