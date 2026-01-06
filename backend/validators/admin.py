from django.contrib import admin
from .models import Validator, ValidatorWallet


class ValidatorInline(admin.StackedInline):
    """Inline admin for Validator model to be used in UserAdmin"""
    model = Validator
    extra = 0  # Don't show empty rows
    max_num = 1  # Only one validator per user
    fields = ('node_version',)
    verbose_name = "Validator Information"
    verbose_name_plural = "Validator Information"
    can_delete = True  # Allow deletion through inline


@admin.register(Validator)
class ValidatorAdmin(admin.ModelAdmin):
    list_display = ('user', 'node_version', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__name', 'node_version')
    list_filter = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {
            'fields': ('user', 'node_version')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ValidatorWallet)
class ValidatorWalletAdmin(admin.ModelAdmin):
    list_display = ('address', 'status', 'operator_address', 'operator', 'moniker', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('address', 'operator_address', 'moniker')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('address', 'status', 'operator_address', 'operator')
        }),
        ('Metadata', {
            'fields': ('moniker', 'logo_uri', 'website', 'description'),
            'classes': ('collapse',)
        }),
        ('Stake Info', {
            'fields': ('v_stake', 'd_stake'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# Note: ValidatorInline is imported and added to UserAdmin in users/admin.py