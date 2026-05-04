from django.contrib import admin

from .models import Stream


@admin.register(Stream)
class StreamAdmin(admin.ModelAdmin):
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
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'description', 'is_active'),
        }),
        ('Channel & Schedule', {
            'fields': ('category', 'starts_at', 'ends_at'),
        }),
        ('Media', {
            'fields': ('url', 'image_url'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Status')
    def computed_status(self, obj):
        return obj.status
