from django.contrib import admin
from .models import ContributionType, Contribution


@admin.register(ContributionType)
class ContributionTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ('user', 'contribution_type', 'points', 'multiplier_at_creation',
                   'frozen_global_points', 'contribution_date', 'created_at')
    list_filter = ('contribution_type', 'contribution_date', 'created_at')
    search_fields = ('user__email', 'user__name', 'contribution_type__name', 'notes')
    readonly_fields = ('frozen_global_points', 'multiplier_at_creation', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'contribution_type', 'points', 'contribution_date', 'evidence_url')
        }),
        ('Points Calculation', {
            'fields': ('multiplier_at_creation', 'frozen_global_points')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )
