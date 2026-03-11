from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Validator, ValidatorWallet, ValidatorWalletStatusSnapshot


class ValidatorWalletInline(admin.TabularInline):
    model = ValidatorWallet
    extra = 0
    fields = ('address', 'network', 'status', 'operator_address', 'moniker', 'v_stake', 'd_stake')
    readonly_fields = ('address', 'network', 'operator_address', 'moniker', 'v_stake', 'd_stake')
    can_delete = False
    show_change_link = True
    verbose_name = "Validator Wallet"
    verbose_name_plural = "Validator Wallets"
    ordering = ('network', '-status', '-created_at')


class ValidatorInline(admin.StackedInline):
    model = Validator
    extra = 0
    max_num = 1
    fields = ('node_version_asimov', 'node_version_bradbury', 'wallet_summary')
    readonly_fields = ('wallet_summary',)
    verbose_name = "Validator Information"
    verbose_name_plural = "Validator Information"
    can_delete = True

    def wallet_summary(self, obj):
        if not obj.pk:
            return '-'
        wallets = ValidatorWallet.objects.filter(operator=obj).order_by('network', '-status')
        if not wallets.exists():
            return format_html('<span style="color: #999;">{}</span>', 'No wallets linked')

        rows = []
        for w in wallets:
            status_color = '#28a745' if w.status == 'active' else '#dc3545' if w.status == 'banned' else '#ffc107'
            rows.append(format_html(
                '<tr>'
                '<td style="padding:2px 8px;font-family:monospace;font-size:12px;">{}</td>'
                '<td style="padding:2px 8px;">{}</td>'
                '<td style="padding:2px 8px;"><span style="color:{};font-weight:bold;">{}</span></td>'
                '</tr>',
                w.address, w.network, status_color, w.status
            ))
        table = mark_safe(
            '<table style="border-collapse:collapse;">'
            '<tr><th style="padding:2px 8px;text-align:left;">Address</th>'
            '<th style="padding:2px 8px;text-align:left;">Network</th>'
            '<th style="padding:2px 8px;text-align:left;">Status</th></tr>'
            + ''.join(rows) +
            '</table>'
        )
        return table
    wallet_summary.short_description = 'Linked Wallets'


@admin.register(Validator)
class ValidatorAdmin(admin.ModelAdmin):
    list_display = ('user', 'node_version_asimov', 'node_version_bradbury', 'wallet_count', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__name', 'node_version_asimov', 'node_version_bradbury')
    list_filter = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    inlines = [ValidatorWalletInline]

    fieldsets = (
        (None, {
            'fields': ('user', 'node_version_asimov', 'node_version_bradbury')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def wallet_count(self, obj):
        return ValidatorWallet.objects.filter(operator=obj).count()
    wallet_count.short_description = 'Wallets'


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
