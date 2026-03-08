from django.contrib import admin
from .models import Validator, ValidatorWallet, ValidatorWalletStatusSnapshot


class ValidatorInline(admin.StackedInline):
    model = Validator
    extra = 0
    max_num = 1
    fields = ('node_version',)
    verbose_name = "Validator Information"
    verbose_name_plural = "Validator Information"
    can_delete = True


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
    list_display = ('address', 'network', 'status', 'operator_address', 'operator', 'moniker', 'created_at')
    list_filter = ('network', 'status', 'created_at')
    search_fields = ('address', 'operator_address', 'moniker')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('address', 'network', 'status', 'operator_address', 'operator')
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


@admin.register(ValidatorWalletStatusSnapshot)
class ValidatorWalletStatusSnapshotAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'date', 'status')
    list_filter = ('status', 'date', 'wallet__network')
    search_fields = ('wallet__address',)
    ordering = ('-date',)
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('wallet',)


# Note: ValidatorInline is imported and added to UserAdmin in users/admin.py
