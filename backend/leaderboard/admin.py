from django.contrib import admin
from .models import ContributionTypeMultiplier, MultiplierPeriod, LeaderboardEntry


class MultiplierPeriodInline(admin.TabularInline):
    model = MultiplierPeriod
    extra = 1
    fields = ('multiplier_value', 'valid_from', 'description')


@admin.register(ContributionTypeMultiplier)
class ContributionTypeMultiplierAdmin(admin.ModelAdmin):
    list_display = ('contribution_type', 'get_current_multiplier', 'get_current_period', 'created_at')
    list_filter = ('contribution_type', 'created_at')
    search_fields = ('contribution_type__name', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MultiplierPeriodInline]
    
    def get_current_multiplier(self, obj):
        return f"{obj.get_current_multiplier_value()}x"
    get_current_multiplier.short_description = "Current Multiplier"
    
    def get_current_period(self, obj):
        latest_period = obj.periods.order_by('-valid_from').first()
        if latest_period:
            return f"Since {latest_period.valid_from.strftime('%Y-%m-%d')}"
        return "No periods defined"
    get_current_period.short_description = "Current Period"


@admin.register(MultiplierPeriod)
class MultiplierPeriodAdmin(admin.ModelAdmin):
    list_display = ('multiplier_with_type', 'multiplier_value', 'valid_from', 'description', 'created_at')
    list_filter = ('multiplier__contribution_type', 'valid_from')
    search_fields = ('multiplier__contribution_type__name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    def multiplier_with_type(self, obj):
        return f"{obj.multiplier.contribution_type.name}"
    multiplier_with_type.short_description = "Contribution Type"


@admin.register(LeaderboardEntry)
class LeaderboardEntryAdmin(admin.ModelAdmin):
    list_display = ('rank', 'user', 'total_points', 'created_at', 'updated_at')
    list_filter = ('rank', 'created_at')
    search_fields = ('user__email', 'user__name')
    readonly_fields = ('total_points', 'rank', 'created_at', 'updated_at')
    ordering = ('rank', '-total_points')
    
    def has_add_permission(self, request):
        # Don't allow manual creation of leaderboard entries
        return False
