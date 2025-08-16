from django.contrib import admin
from .models import Builder


class BuilderInline(admin.StackedInline):
    """Inline admin for Builder model to be used in UserAdmin"""
    model = Builder
    extra = 0  # Don't show empty rows
    max_num = 1  # Only one builder per user
    fields = ()  # No fields yet, model is empty
    verbose_name = "Builder Information"
    verbose_name_plural = "Builder Information"
    can_delete = True  # Allow deletion through inline


@admin.register(Builder)
class BuilderAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__name')
    list_filter = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
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


# Note: BuilderInline is imported and added to UserAdmin in users/admin.py