from django.contrib import admin

from .models import Partner


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
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
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'is_active'),
        }),
        ('URLs', {
            'fields': ('logo_url', 'website_url', 'url'),
        }),
        ('Display', {
            'fields': ('display_order',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
