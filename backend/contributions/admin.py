from django.contrib import admin
from .models import ContributionType, Contribution
from leaderboard.models import GlobalLeaderboardMultiplier


class GlobalLeaderboardMultiplierInline(admin.TabularInline):
    model = GlobalLeaderboardMultiplier
    extra = 1
    fields = ('multiplier_value', 'valid_from', 'description')


@admin.register(ContributionType)
class ContributionTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_current_multiplier', 'description', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [GlobalLeaderboardMultiplierInline]
    
    def get_current_multiplier(self, obj):
        from leaderboard.models import GlobalLeaderboardMultiplier
        return f"{GlobalLeaderboardMultiplier.get_current_multiplier_value(obj)}x"
    get_current_multiplier.short_description = "Current Multiplier"


@admin.register(GlobalLeaderboardMultiplier)
class GlobalLeaderboardMultiplierAdmin(admin.ModelAdmin):
    list_display = ('contribution_type', 'multiplier_value', 'valid_from', 'description', 'created_at')
    list_filter = ('contribution_type', 'valid_from')
    search_fields = ('contribution_type__name', 'description', 'notes')
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
