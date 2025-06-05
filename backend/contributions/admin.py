from django.contrib import admin
from django.core.management import call_command
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse, path
from django.shortcuts import render
from django.utils import timezone
from django.utils.html import format_html
from .models import ContributionType, Contribution, SubmittedContribution, Evidence
from leaderboard.models import GlobalLeaderboardMultiplier


class GlobalLeaderboardMultiplierInline(admin.TabularInline):
    model = GlobalLeaderboardMultiplier
    extra = 1
    fields = ('multiplier_value', 'valid_from', 'description')


@admin.register(ContributionType)
class ContributionTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_current_multiplier', 'min_points', 'max_points', 'description', 'created_at')
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
        if obj and obj.file:
            return format_html('<a href="{}" target="_blank">View file</a>', obj.file.url)
        return '-'
    file_preview.short_description = 'Preview'
    
    def get_extra(self, request, obj=None, **kwargs):
        """Dynamically set the number of extra forms based on whether evidence already exists."""
        if obj and obj.evidence_items.exists():
            return 0  # No extra forms if evidence already exists
        return 1  # One extra form if no evidence
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Set the appropriate foreign key based on the parent model
        if obj:
            if obj.__class__.__name__ == 'Contribution':
                # For contributions, only show contribution field
                formset.form.base_fields.pop('submitted_contribution', None)
            elif obj.__class__.__name__ == 'SubmittedContribution':
                # For submitted contributions, only show submitted_contribution field
                formset.form.base_fields.pop('contribution', None)
        return formset


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ('user', 'contribution_type', 'points', 'multiplier_at_creation',
                   'frozen_global_points', 'contribution_date', 'source_submission_link', 'created_at')
    list_filter = ('contribution_type', 'contribution_date', 'created_at')
    search_fields = ('user__email', 'user__name', 'contribution_type__name', 'notes')
    readonly_fields = ('frozen_global_points', 'multiplier_at_creation', 'created_at', 'updated_at', 
                      'source_submission_link', 'contribution_type_info')
    ordering = ('-created_at', '-contribution_date')  # Most recent contributions first
    inlines = [EvidenceInline]
    fieldsets = (
        (None, {
            'fields': ('user', 'contribution_type', 'contribution_type_info', 'points', 'contribution_date')
        }),
        ('Points Calculation', {
            'fields': ('multiplier_at_creation', 'frozen_global_points')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
        ('Source', {
            'fields': ('source_submission_link',),
            'classes': ('collapse',)
        })
    )
    
    def source_submission_link(self, obj):
        # source_submission is a reverse relation, so we need to use .first() or .exists()
        source_submission = obj.source_submission.first() if hasattr(obj, 'source_submission') else None
        if source_submission:
            url = f"/admin/contributions/submittedcontribution/{source_submission.id}/change/"
            return format_html('<a href="{}">View Submission</a>', url)
        return '-'
    source_submission_link.short_description = 'Source Submission'
    
    def contribution_type_info(self, obj):
        if obj and obj.contribution_type:
            ct = obj.contribution_type
            try:
                current_multiplier = GlobalLeaderboardMultiplier.get_current_multiplier_value(ct)
            except:
                current_multiplier = 1.0
            
            return format_html(
                '<div id="contribution-type-info" style="padding: 10px; background: #f8f9fa; border-radius: 4px; margin: 5px 0;">'
                '<strong>Points Range:</strong> {}-{} points<br>'
                '<strong>Current Multiplier:</strong> {}x<br>'
                '{}'
                '</div>',
                ct.min_points,
                ct.max_points,
                current_multiplier,
                f'<strong>Description:</strong> {ct.description}' if ct.description else ''
            )
        return '-'
    contribution_type_info.short_description = 'Contribution Type Info'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('run-daily-uptime/', self.admin_site.admin_view(self.run_daily_uptime_view), name='run_daily_uptime'),
            path('contribution-type-info/<int:pk>/', self.admin_site.admin_view(self.contribution_type_info_view), name='contribution_type_info'),
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
    
    def contribution_type_info_view(self, request, pk):
        """API endpoint to get contribution type info."""
        try:
            ct = ContributionType.objects.get(pk=pk)
            try:
                current_multiplier = GlobalLeaderboardMultiplier.get_current_multiplier_value(ct)
            except:
                current_multiplier = 1.0
            
            return JsonResponse({
                'min_points': ct.min_points,
                'max_points': ct.max_points,
                'current_multiplier': current_multiplier,
                'description': ct.description
            })
        except ContributionType.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)
    
    def get_queryset(self, request):
        """Optimize queryset to avoid N+1 queries."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'contribution_type').prefetch_related('source_submission')
    
    class Media:
        js = ('admin/js/contribution_type_dynamic.js',)


@admin.register(SubmittedContribution)
class SubmittedContributionAdmin(admin.ModelAdmin):
    list_display = ('user', 'contribution_type', 'state', 'contribution_date', 
                   'created_at', 'reviewed_by')
    list_filter = ('state', 'contribution_type', 'created_at', 'reviewed_at')
    search_fields = ('user__email', 'user__name', 'notes', 'staff_reply')
    date_hierarchy = 'created_at'
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_edited_at', 
                      'converted_contribution_link', 'contribution_type_info')
    inlines = [EvidenceInline]
    
    fieldsets = (
        ('Submission Info', {
            'fields': ('id', 'user', 'contribution_type', 'contribution_type_info', 'contribution_date', 'notes')
        }),
        ('Review Status', {
            'fields': ('state', 'staff_reply', 'reviewed_by', 'reviewed_at')
        }),
        ('Tracking', {
            'fields': ('created_at', 'updated_at', 'last_edited_at', 'converted_contribution_link'),
            'classes': ('collapse',)
        })
    )
    
    def converted_contribution_link(self, obj):
        if obj.converted_contribution:
            url = f"/admin/contributions/contribution/{obj.converted_contribution.id}/change/"
            return format_html('<a href="{}">View Contribution</a>', url)
        return '-'
    converted_contribution_link.short_description = 'Converted Contribution'
    
    def contribution_type_info(self, obj):
        if obj and obj.contribution_type:
            ct = obj.contribution_type
            try:
                current_multiplier = GlobalLeaderboardMultiplier.get_current_multiplier_value(ct)
            except:
                current_multiplier = 1.0
            
            return format_html(
                '<div id="contribution-type-info" style="padding: 10px; background: #f8f9fa; border-radius: 4px; margin: 5px 0;">'
                '<strong>Points Range:</strong> {}-{} points<br>'
                '<strong>Current Multiplier:</strong> {}x<br>'
                '{}'
                '</div>',
                ct.min_points,
                ct.max_points,
                current_multiplier,
                f'<strong>Description:</strong> {ct.description}' if ct.description else ''
            )
        return '-'
    contribution_type_info.short_description = 'Contribution Type Info'
    
    def save_model(self, request, obj, form, change):
        """Update review fields when state changes."""
        if change and 'state' in form.changed_data:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        
        # Update last_edited_at if notes changed and state is more_info_needed
        if change and 'notes' in form.changed_data and obj.state == 'more_info_needed':
            obj.last_edited_at = timezone.now()
            
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        """Make fields readonly for accepted submissions."""
        readonly = list(self.readonly_fields)
        if obj and obj.state == 'accepted':
            readonly.extend(['user', 'contribution_date', 'notes'])
        return readonly
    
    class Media:
        js = ('admin/js/contribution_type_dynamic.js',)


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'evidence_type', 'parent_object', 'has_description', 
                   'has_url', 'has_file', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('description', 'url')
    readonly_fields = ('created_at', 'updated_at')
    
    def evidence_type(self, obj):
        if obj.contribution:
            return 'Contribution'
        elif obj.submitted_contribution:
            return 'Submission'
        return 'None'
    evidence_type.short_description = 'Type'
    
    def parent_object(self, obj):
        if obj.contribution:
            return str(obj.contribution)
        elif obj.submitted_contribution:
            return str(obj.submitted_contribution)
        return '-'
    parent_object.short_description = 'Parent'
    
    def has_description(self, obj):
        return bool(obj.description)
    has_description.boolean = True
    has_description.short_description = 'Desc'
    
    def has_url(self, obj):
        return bool(obj.url)
    has_url.boolean = True
    has_url.short_description = 'URL'
    
    def has_file(self, obj):
        return bool(obj.file)
    has_file.boolean = True
    has_file.short_description = 'File'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('contribution__user', 'submitted_contribution__user', 
                               'contribution__contribution_type', 'submitted_contribution__contribution_type')