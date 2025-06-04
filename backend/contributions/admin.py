from django.contrib import admin
from django.core.management import call_command
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse, path
from django.shortcuts import render
from .models import ContributionType, Contribution, Evidence
from leaderboard.models import GlobalLeaderboardMultiplier


class GlobalLeaderboardMultiplierInline(admin.TabularInline):
    model = GlobalLeaderboardMultiplier
    extra = 1
    fields = ('multiplier_value', 'valid_from', 'description')


@admin.register(ContributionType)
class ContributionTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_current_multiplier', 'description', 'created_at')
    list_display_links = ('get_current_multiplier',)
    list_editable = ('name', 'description')
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


class EvidenceInline(admin.TabularInline):
    model = Evidence
    extra = 1
    fields = ('description', 'url', 'file', 'file_preview')
    readonly_fields = ('file_preview',)
    verbose_name = "Evidence Item"
    verbose_name_plural = "Evidence Items"
    
    def file_preview(self, obj):
        """Display a preview link for the file if it exists."""
        from django.utils.html import format_html
        if obj and obj.file:
            return format_html('<a href="{}" target="_blank">View file</a>', obj.file.url)
        return '-'
    file_preview.short_description = 'Preview'
    
    def get_extra(self, request, obj=None, **kwargs):
        """Dynamically set the number of extra forms based on whether evidence already exists."""
        if obj and obj.evidence_items.exists():
            return 0  # No extra forms if evidence already exists
        return 1  # One extra form if no evidence


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ('user', 'contribution_type', 'points', 'multiplier_at_creation',
                   'frozen_global_points', 'contribution_date', 'created_at')
    list_filter = ('contribution_type', 'contribution_date', 'created_at')
    search_fields = ('user__email', 'user__name', 'contribution_type__name', 'notes')
    readonly_fields = ('frozen_global_points', 'multiplier_at_creation', 'created_at', 'updated_at')
    ordering = ('-created_at', '-contribution_date')  # Most recent contributions first
    inlines = [EvidenceInline]
    fieldsets = (
        (None, {
            'fields': ('user', 'contribution_type', 'points', 'contribution_date')
        }),
        ('Points Calculation', {
            'fields': ('multiplier_at_creation', 'frozen_global_points')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('run-daily-uptime/', self.admin_site.admin_view(self.run_daily_uptime_view), name='run_daily_uptime'),
        ]
        return custom_urls + urls
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['has_run_uptime_permission'] = request.user.is_superuser
        return super().changelist_view(request, extra_context=extra_context)
    
    def run_daily_uptime_view(self, request):
        if request.method == 'POST':
            try:
                # Run the command with default options
                call_command('add_daily_uptime', '--verbose')
                messages.success(request, 'Daily uptime update completed successfully!')
            except Exception as e:
                messages.error(request, f'Error running daily uptime update: {str(e)}')
            
            return HttpResponseRedirect(reverse('admin:contributions_contribution_changelist'))
        
        context = {
            'title': 'Run Daily Uptime Update',
            'opts': self.model._meta,
            'has_change_permission': request.user.has_perm('contributions.change_contribution')
        }
        return render(request, 'admin/contributions/run_daily_uptime.html', context)


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ('contribution', 'description', 'url', 'has_file', 'file_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('description', 'url', 'contribution__user__email', 'contribution__user__name')
    readonly_fields = ('file_preview', 'created_at', 'updated_at')
    
    def has_file(self, obj):
        return bool(obj.file)
    has_file.boolean = True
    has_file.short_description = "Has File"
    
    def file_preview(self, obj):
        """Display a preview link for the file if it exists."""
        from django.utils.html import format_html
        if obj and obj.file:
            return format_html('<a href="{}" target="_blank">View file</a>', obj.file.url)
        return '-'
    file_preview.short_description = 'Preview'
