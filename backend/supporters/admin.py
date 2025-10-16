from django.contrib import admin
from .models import Supporter


@admin.register(Supporter)
class SupporterAdmin(admin.ModelAdmin):
    """
    Admin interface for Supporter model.
    """
    list_display = ['user', 'created_at', 'updated_at']
    search_fields = ['user__email', 'user__name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
