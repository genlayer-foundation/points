from django.contrib import admin
from .models import Creator


@admin.register(Creator)
class CreatorAdmin(admin.ModelAdmin):
    """
    Admin interface for Creator model.
    """
    list_display = ['user', 'created_at', 'updated_at']
    search_fields = ['user__email', 'user__name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
