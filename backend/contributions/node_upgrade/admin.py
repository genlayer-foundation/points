from django.contrib import admin
from .models import TargetNodeVersion


@admin.register(TargetNodeVersion)
class TargetNodeVersionAdmin(admin.ModelAdmin):
    list_display = ('version', 'target_date', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'target_date')
    search_fields = ('version',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('version', 'target_date', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """
        Make certain fields readonly after creation.
        """
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:  # If editing existing object
            # Optionally make version readonly after creation
            # readonly_fields = readonly_fields + ('version',)
            pass
        return readonly_fields