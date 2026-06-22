from django.contrib import admin
from django import forms
from django.core.management import call_command
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse, path
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.html import format_html
from django.db import transaction
from django.db.models import (
    Count,
    DecimalField,
    Exists,
    F,
    IntegerField,
    OuterRef,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from datetime import datetime
from .models import (
    Category,
    ContributionType,
    Contribution,
    SubmittedContribution,
    Evidence,
    ContributionHighlight,
    Mission,
    StartupRequest,
    SubmissionNote,
    FeaturedContent,
    Alert,
    BlocklistedURL,
    EvidenceURLType,
    ProjectMilestoneReview,
    ContributionDiscordXPState,
    DiscordXPDistributionEvent,
)
from .validator_forms import CreateValidatorForm
from leaderboard.models import GlobalLeaderboardMultiplier
from social_connections.models import DiscordRole
from utils.admin_mixins import CloudinaryUploadMixin
from notifications import services as notification_services
from notifications.admin_mixins import BroadcastNotificationAdminMixin

User = get_user_model()

NON_CAPACITY_STATES = ['rejected', 'canceled']


class FeaturedContentAdminForm(forms.ModelForm):
    hero_placements = forms.MultipleChoiceField(
        choices=FeaturedContent.HERO_PLACEMENT_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=(
            "For hero banners only. Select 'All hero surfaces' or choose one "
            "or more specific surfaces."
        ),
    )

    class Meta:
        model = FeaturedContent
        fields = '__all__'

    def clean_hero_placements(self):
        return FeaturedContent.normalize_hero_placements(
            self.cleaned_data.get('hero_placements', [])
        )


def active_submission_count_subquery(fk_name):
    return SubmittedContribution.objects.exclude(
        state__in=NON_CAPACITY_STATES
    ).filter(
        **{fk_name: OuterRef('pk')}
    ).values(
        fk_name
    ).annotate(
        count=Count('pk')
    ).values('count')


def coalesced_count(subquery):
    return Coalesce(
        Subquery(subquery, output_field=IntegerField()),
        Value(0),
        output_field=IntegerField(),
    )


class ContributionTypeListFilter(admin.SimpleListFilter):
    title = 'contribution type'
    parameter_name = 'contribution_type__id__exact'

    def lookups(self, request, model_admin):
        _ = model_admin
        contribution_types = ContributionType.objects.select_related(
            'category'
        ).order_by('category__name', 'name')
        return [
            (
                str(contribution_type.id),
                str(contribution_type),
            )
            for contribution_type in contribution_types
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(contribution_type_id=self.value())
        return queryset


class ReadOnlyAdminMixin:
    actions = None

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'description', 'created_at')
    search_fields = ('name', 'slug', 'description')
    readonly_fields = ('created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}


class GlobalLeaderboardMultiplierInline(admin.TabularInline):
    model = GlobalLeaderboardMultiplier
    extra = 1
    fields = ('multiplier_value', 'valid_from', 'description')


@admin.register(ContributionType)
class ContributionTypeAdmin(BroadcastNotificationAdminMixin, admin.ModelAdmin):
    broadcast_event_slug = 'contribution_type.published'
    broadcast_service = staticmethod(notification_services.broadcast_contribution_type)
    broadcast_eligible = staticmethod(lambda obj: obj.is_submittable)
    broadcast_ineligible_reason = 'the contribution type is not submittable'
    list_display = (
        'name', 'category', 'review_flow', 'is_default', 'is_submittable',
        'get_submission_usage', 'show_in_contributions',
        'get_current_multiplier', 'min_points', 'max_points', 'rubric_extra_points',
        'description', 'created_at',
    )
    list_display_links = ('get_current_multiplier',)
    list_editable = (
        'name',
        'review_flow',
        'is_default',
        'is_submittable',
        'show_in_contributions',
        'rubric_extra_points',
        'description',
    )
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    list_filter = ('category', 'review_flow', 'is_default', 'is_submittable', 'show_in_contributions')
    # Auto-fill slug from name on the edit page
    prepopulated_fields = { 'slug': ('name',) }
    filter_horizontal = (
        'required_discord_roles',
        'accepted_evidence_url_types',
        'required_evidence_url_types',
    )
    inlines = [GlobalLeaderboardMultiplierInline]
    show_facets = admin.ShowFacets.NEVER

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        multiplier_field = DecimalField(max_digits=10, decimal_places=2)
        current_multiplier = GlobalLeaderboardMultiplier.objects.filter(
            contribution_type_id=OuterRef('pk')
        ).order_by('-valid_from').values('multiplier_value')[:1]

        return qs.select_related('category').annotate(
            submission_count=coalesced_count(
                active_submission_count_subquery('contribution_type_id')
            ),
            current_multiplier_value=Coalesce(
                Subquery(current_multiplier, output_field=multiplier_field),
                Value(1.0, output_field=multiplier_field),
                output_field=multiplier_field,
            ),
        )
    
    def get_current_multiplier(self, obj):
        multiplier = getattr(obj, 'current_multiplier_value', None)
        if multiplier is None:
            multiplier = GlobalLeaderboardMultiplier.get_current_multiplier_value(obj)
        return f"{multiplier}x"
    get_current_multiplier.short_description = "Current Multiplier"

    def get_submission_usage(self, obj):
        count = obj.get_submission_count()
        if obj.max_submissions is None:
            return f'{count} / Unlimited'
        return f'{count} / {obj.max_submissions}'
    get_submission_usage.short_description = 'Submissions'

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'required_discord_roles':
            kwargs['queryset'] = DiscordRole.objects.filter(
                deleted_at__isnull=True,
            ).exclude(
                role_id=F('guild_id'),
            ).order_by('guild_id', '-position', 'name')
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(GlobalLeaderboardMultiplier)
class GlobalLeaderboardMultiplierAdmin(admin.ModelAdmin):
    list_display = ('contribution_type', 'multiplier_value', 'valid_from', 'description', 'created_at')
    list_filter = (ContributionTypeListFilter, 'valid_from')
    search_fields = ('contribution_type__name', 'description', 'notes')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ProjectMilestoneReview)
class ProjectMilestoneReviewAdmin(admin.ModelAdmin):
    list_select_related = (
        'submitted_contribution__user',
        'submitted_contribution__contribution_type',
        'submitted_contribution__proposed_contribution_type',
        'proposer',
    )
    list_display = (
        'submitted_contribution',
        'review_flow',
        'action',
        'confidence',
        'proposer',
        'updated_at',
    )
    list_filter = ('review_flow', 'action', 'confidence')
    search_fields = (
        'submitted_contribution__title',
        'submitted_contribution__user__email',
        'submitted_contribution__user__address',
        'proposer__email',
        'proposer__address',
    )
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('submitted_contribution', 'proposer')


class ContributionHighlightInline(admin.TabularInline):
    model = ContributionHighlight
    extra = 1
    fields = ('title', 'description', 'created_at')
    readonly_fields = ('created_at',)
    verbose_name = "Highlight"
    verbose_name_plural = "Highlights"
    
    def get_extra(self, request, obj=None, **kwargs):
        """Only show extra form if no highlights exist."""
        if obj and obj.highlights.exists():
            return 0
        return 1


class EvidenceInline(admin.TabularInline):
    model = Evidence
    extra = 1
    fields = ('description', 'url', 'url_type', 'file', 'file_preview')
    readonly_fields = ('url_type', 'file_preview',)
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
    list_display = ('id', 'user_display', 'user_address_short', 'contribution_type', 'points',
                   'frozen_global_points', 'contribution_date_display', 'has_evidence',
                   'has_highlight', 'created_at')
    list_filter = ('contribution_type__category', ContributionTypeListFilter, 'contribution_date', 'created_at',
                  ('evidence_items', admin.EmptyFieldListFilter))
    search_fields = ('user__email', 'user__name', 'user__address', 'contribution_type__name',
                    'notes', 'evidence_items__description', 'evidence_items__url', 'mission__name')
    readonly_fields = ('created_at', 'updated_at', 
                      'source_submission_link', 'contribution_type_info')
    ordering = ('-contribution_date', '-created_at')  # Most recent contributions first
    inlines = [ContributionHighlightInline, EvidenceInline]
    list_per_page = 50
    list_select_related = ['user', 'contribution_type']
    autocomplete_fields = ['user', 'contribution_type']
    show_full_result_count = False
    show_facets = admin.ShowFacets.NEVER
    change_form_template = 'admin/contributions/contribution_change_form.html'
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
            path('create-validator/', self.admin_site.admin_view(self.create_validator_view), name='contributions_create_validator'),
            path('run-daily-uptime/', self.admin_site.admin_view(self.run_daily_uptime_view), name='run_daily_uptime'),
            path('contribution-type-info/<int:pk>/', self.admin_site.admin_view(self.contribution_type_info_view), name='contribution_type_info'),
        ]
        return custom_urls + urls
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['has_run_uptime_permission'] = request.user.is_superuser
        extra_context['has_create_validator_permission'] = request.user.is_superuser
        return super().changelist_view(request, extra_context=extra_context)
    
    def create_validator_view(self, request):
        """View for creating a new validator."""
        if request.method == 'POST':
            form = CreateValidatorForm(request.POST)
            if form.is_valid():
                try:
                    user = self._process_validator_creation(form)
                    messages.success(request, f'Validator {user.address or user.email} created successfully with contributions.')
                    # Redirect to user detail page
                    return redirect(reverse('admin:users_user_change', args=[user.id]))
                except ValidationError as e:
                    messages.error(request, str(e))
                except Exception as e:
                    messages.error(request, f'Error creating validator: {str(e)}')
        else:
            form = CreateValidatorForm()
        
        # Get contribution types for display
        default_types = ContributionType.objects.filter(is_default=True).order_by('name')
        
        context = {
            'form': form,
            'title': 'Create Validator',
            'default_types': default_types,
            'opts': self.model._meta,
            'has_view_permission': True,
            'has_add_permission': True,
            'has_change_permission': True,
            'has_delete_permission': True,
        }
        
        return render(request, 'admin/contributions/create_validator.html', context)
    
    @transaction.atomic
    def _process_validator_creation(self, form):
        """Process the validator creation with contributions."""
        name = form.cleaned_data['name']
        address = form.cleaned_data['address']
        contribution_date = form.cleaned_data['contribution_date']
        
        # Look up or create user
        user, created = User.objects.get_or_create(
            address=address,
            defaults={
                'email': f'{address}@validator.local',  # Generate a valid email from address
                'username': address,
                'visible': True,
            }
        )
        
        # Update name if provided (and different)
        if name and user.name != name:
            user.name = name
            user.save()

        from validators.models import Validator
        Validator.objects.create(user=user)
        
        # Get selected contributions
        contributions_data = form.get_selected_contributions()
        
        # Convert date to datetime
        contribution_datetime = datetime.combine(contribution_date, datetime.min.time())
        contribution_datetime = timezone.make_aware(contribution_datetime)
        
        # Create contributions
        created_contributions = []
        for contrib_data in contributions_data:
            contribution_type = ContributionType.objects.get(id=contrib_data['contribution_type_id'])
            
            # Check for duplicates
            existing = Contribution.objects.filter(
                user=user,
                contribution_type=contribution_type,
                contribution_date__date=contribution_date
            ).exists()
            
            if existing:
                raise ValidationError(
                    f'Contribution of type "{contribution_type.name}" already exists for user {user.email} on {contribution_date}'
                )
            
            # Create the contribution
            contribution = Contribution.objects.create(
                user=user,
                contribution_type=contribution_type,
                points=contrib_data['points'],
                contribution_date=contribution_datetime,
                notes=f'Created via validator creation on {timezone.now().strftime("%Y-%m-%d %H:%M")}'
            )
            created_contributions.append(contribution)
        
        return user
    
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
        """Keep the contribution changelist cheap for large contribution tables."""
        qs = super().get_queryset(request)
        return qs.select_related(
            'user',
            'contribution_type',
            'contribution_type__category',
        ).annotate(
            has_evidence_value=Exists(
                Evidence.objects.filter(contribution_id=OuterRef('pk'))
            ),
            has_highlight_value=Exists(
                ContributionHighlight.objects.filter(contribution_id=OuterRef('pk'))
            ),
        )
    
    def user_display(self, obj):
        """Display user name with email."""
        if obj.user.name:
            return f"{obj.user.name}"
        return obj.user.email
    user_display.short_description = 'User'
    user_display.admin_order_field = 'user__name'
    
    def user_address_short(self, obj):
        """Display shortened wallet address."""
        if obj.user.address:
            return f"{obj.user.address[:6]}...{obj.user.address[-4:]}"
        return '-'
    user_address_short.short_description = 'Address'
    
    def contribution_date_display(self, obj):
        """Display formatted contribution date."""
        if obj.contribution_date:
            return obj.contribution_date.strftime('%b %d, %Y')
        return '-'
    contribution_date_display.short_description = 'Date'
    contribution_date_display.admin_order_field = 'contribution_date'
    
    def has_evidence(self, obj):
        """Check if contribution has evidence."""
        annotated = getattr(obj, 'has_evidence_value', None)
        if annotated is not None:
            return annotated
        return obj.evidence_items.exists()
    has_evidence.boolean = True
    has_evidence.short_description = 'Evidence'
    
    def has_highlight(self, obj):
        """Check if contribution has a highlight."""
        annotated = getattr(obj, 'has_highlight_value', None)
        if annotated is not None:
            return annotated
        return obj.highlights.exists()
    has_highlight.boolean = True
    has_highlight.short_description = 'Highlighted'
    
    class Media:
        js = ('admin/js/contribution_type_dynamic.js',)


@admin.register(ContributionDiscordXPState)
class ContributionDiscordXPStateAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        'source_link',
        'contributor',
        'discord_username',
        'entry_type',
        'community_points',
        'awarded_amount',
        'pending_amount_display',
        'status',
        'last_copied_at',
        'distributed_at',
    )
    list_filter = (
        'status',
        'contribution__contribution_type__category',
        'contribution__contribution_type',
        'social_task_completion__task',
        'last_copied_at',
        'distributed_at',
    )
    search_fields = (
        'contribution__id',
        'contribution__title',
        'contribution__notes',
        'contribution__user__name',
        'contribution__user__email',
        'contribution__user__address',
        'contribution__user__discordconnection__platform_username',
        'contribution__user__discordconnection__guild_nick',
        'contribution__contribution_type__name',
        'social_task_completion__task__name',
        'social_task_completion__task__slug',
        'social_task_completion__user__name',
        'social_task_completion__user__email',
        'social_task_completion__user__address',
        'social_task_completion__user__discordconnection__platform_username',
        'social_task_completion__user__discordconnection__guild_nick',
    )
    ordering = ('-created_at',)
    show_facets = admin.ShowFacets.NEVER

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'contribution',
            'contribution__user',
            'contribution__user__discordconnection',
            'contribution__contribution_type',
            'contribution__contribution_type__category',
            'social_task_completion',
            'social_task_completion__user',
            'social_task_completion__user__discordconnection',
            'social_task_completion__task',
        )

    def source_link(self, obj):
        if obj.contribution_id:
            url = reverse('admin:contributions_contribution_change', args=[obj.contribution_id])
            return format_html('<a href="{}">Contribution #{}</a>', url, obj.contribution_id)
        url = reverse('admin:social_tasks_socialtaskcompletion_change', args=[obj.social_task_completion_id])
        return format_html('<a href="{}">Task completion #{}</a>', url, obj.social_task_completion_id)
    source_link.short_description = 'Source'
    source_link.admin_order_field = 'contribution_id'

    def contributor(self, obj):
        user = obj.recipient
        return user.name or user.email or user.address
    contributor.admin_order_field = 'contribution__user__name'

    def discord_username(self, obj):
        connection = getattr(obj.recipient, 'discordconnection', None)
        if not connection:
            return '-'
        return connection.guild_nick or connection.platform_username or '-'
    discord_username.short_description = 'Discord'

    def entry_type(self, obj):
        if obj.contribution_id:
            return obj.contribution.contribution_type
        return obj.social_task_completion.task
    entry_type.short_description = 'Type / task'
    entry_type.admin_order_field = 'contribution__contribution_type'

    def community_points(self, obj):
        return obj.target_amount

    def pending_amount_display(self, obj):
        return obj.pending_amount
    pending_amount_display.short_description = 'Pending'


@admin.register(DiscordXPDistributionEvent)
class DiscordXPDistributionEventAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        'created_at',
        'action',
        'source_link',
        'contributor',
        'discord_username',
        'amount',
        'actor',
    )
    list_filter = (
        'action',
        'created_at',
        'state__contribution__contribution_type__category',
        'state__contribution__contribution_type',
        'state__social_task_completion__task',
    )
    search_fields = (
        'state__contribution__id',
        'state__contribution__title',
        'state__contribution__user__name',
        'state__contribution__user__email',
        'state__contribution__user__address',
        'state__contribution__user__discordconnection__platform_username',
        'state__contribution__user__discordconnection__guild_nick',
        'state__social_task_completion__task__name',
        'state__social_task_completion__task__slug',
        'state__social_task_completion__user__name',
        'state__social_task_completion__user__email',
        'state__social_task_completion__user__address',
        'state__social_task_completion__user__discordconnection__platform_username',
        'state__social_task_completion__user__discordconnection__guild_nick',
        'actor__name',
        'actor__email',
    )
    ordering = ('-created_at',)
    show_facets = admin.ShowFacets.NEVER

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'state',
            'state__contribution',
            'state__contribution__user',
            'state__contribution__user__discordconnection',
            'state__contribution__contribution_type',
            'state__social_task_completion',
            'state__social_task_completion__user',
            'state__social_task_completion__user__discordconnection',
            'state__social_task_completion__task',
            'actor',
        )

    def source_link(self, obj):
        if obj.state.contribution_id:
            url = reverse('admin:contributions_contribution_change', args=[obj.state.contribution_id])
            return format_html('<a href="{}">Contribution #{}</a>', url, obj.state.contribution_id)
        url = reverse('admin:social_tasks_socialtaskcompletion_change', args=[obj.state.social_task_completion_id])
        return format_html('<a href="{}">Task completion #{}</a>', url, obj.state.social_task_completion_id)
    source_link.short_description = 'Source'
    source_link.admin_order_field = 'state__contribution_id'

    def contributor(self, obj):
        user = obj.state.recipient
        return user.name or user.email or user.address
    contributor.admin_order_field = 'state__contribution__user__name'

    def discord_username(self, obj):
        connection = getattr(obj.state.recipient, 'discordconnection', None)
        if not connection:
            return '-'
        return connection.guild_nick or connection.platform_username or '-'
    discord_username.short_description = 'Discord'


class SubmissionNoteInline(admin.TabularInline):
    model = SubmissionNote
    extra = 0
    readonly_fields = ('user', 'message', 'is_proposal', 'created_at')
    fields = ('user', 'message', 'is_proposal', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SubmittedContribution)
class SubmittedContributionAdmin(admin.ModelAdmin):
    list_display = ('user', 'contribution_type', 'proposed_points', 'state', 'gate_reviewed',
                   'contribution_date', 'created_at', 'reviewed_by')
    list_filter = ('state', 'gate_reviewed', 'contribution_type__category', ContributionTypeListFilter, 'created_at', 'reviewed_at')
    search_fields = ('user__email', 'user__name', 'notes', 'staff_reply', 'mission__name')
    list_per_page = 25
    show_full_result_count = False
    show_facets = admin.ShowFacets.NEVER
    autocomplete_fields = ('user', 'contribution_type', 'reviewed_by')
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_edited_at',
                      'converted_contribution_link', 'contribution_type_info', 'proposed_points')
    inlines = [EvidenceInline, SubmissionNoteInline]
    
    fieldsets = (
        ('Submission Info', {
            'fields': ('id', 'user', 'contribution_type', 'contribution_type_info', 'proposed_points', 'contribution_date', 'notes')
        }),
        ('Review Status', {
            'fields': ('state', 'gate_reviewed', 'staff_reply', 'reviewed_by', 'reviewed_at')
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

    def get_queryset(self, request):
        """Keep the changelist query cheap for large submission tables."""
        qs = super().get_queryset(request)
        return qs.select_related(
            'user',
            'contribution_type',
            'contribution_type__category',
            'reviewed_by',
            'mission',
        )

    class Media:
        js = ('admin/js/contribution_type_dynamic.js',)


@admin.register(EvidenceURLType)
class EvidenceURLTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_generic', 'allow_duplicate', 'order', 'ownership_social_account', 'created_at')
    list_filter = ('is_generic', 'allow_duplicate')
    list_editable = ('allow_duplicate',)
    search_fields = ('name', 'slug', 'description')
    readonly_fields = ('created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order', 'name')


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'evidence_type', 'parent_object', 'url_type',
                   'has_description', 'has_url', 'has_file', 'created_at')
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
                               'contribution__contribution_type', 'submitted_contribution__contribution_type',
                               'url_type')


@admin.register(BlocklistedURL)
class BlocklistedURLAdmin(admin.ModelAdmin):
    list_display = ('url_prefix', 'reason', 'created_at')
    search_fields = ('url_prefix', 'reason')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ContributionHighlight)
class ContributionHighlightAdmin(admin.ModelAdmin):
    list_display = ('title', 'contribution_id_display', 'contribution_type', 'user_display', 'points_display', 'contribution_date_display', 'created_at')
    list_filter = ('contribution__contribution_type', 'created_at')
    search_fields = ('title', 'description', 'contribution__id', 'contribution__user__name', 
                     'contribution__user__email', 'contribution__notes')
    ordering = ['-contribution__contribution_date']
    readonly_fields = ('created_at', 'updated_at', 'contribution_details')
    raw_id_fields = ('contribution',)  # Show only ID in the field
    
    fieldsets = (
        ('Highlight Information', {
            'fields': ('title', 'description', 'contribution')
        }),
        ('Contribution Details', {
            'fields': ('contribution_details',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def contribution_id_display(self, obj):
        """Display contribution ID with link."""
        if obj.contribution:
            url = reverse('admin:contributions_contribution_change', args=[obj.contribution.id])
            return format_html('<a href="{}">#{}</a>', url, obj.contribution.id)
        return '-'
    contribution_id_display.short_description = 'Contribution ID'
    
    def user_display(self, obj):
        """Display user name."""
        if obj.contribution and obj.contribution.user:
            return obj.contribution.user.name or obj.contribution.user.email
        return '-'
    user_display.short_description = 'User'
    
    def points_display(self, obj):
        """Display points earned."""
        if obj.contribution:
            return obj.contribution.frozen_global_points
        return '-'
    points_display.short_description = 'Points'

    def contribution_type(self, obj):
        """Display the contribution type."""
        if obj.contribution:
            return obj.contribution.contribution_type.name
        return '-'
    contribution_type.short_description = 'Type'
    
    def contribution_date_display(self, obj):
        """Display the contribution date."""
        if obj.contribution:
            return obj.contribution.contribution_date
        return '-'
    contribution_date_display.short_description = 'Contribution Date'
    
    def contribution_details(self, obj):
        """Display detailed information about the contribution."""
        if obj and obj.contribution:
            contrib = obj.contribution
            user = contrib.user
            
            return format_html(
                '<div style="padding: 10px; background: #f8f9fa; border-radius: 4px;">'
                '<strong>User:</strong> {} ({})<br>'
                '<strong>Type:</strong> {}<br>'
                '<strong>Points:</strong> {} (Global: {})<br>'
                '<strong>Date:</strong> {}<br>'
                '<strong>Notes:</strong> {}'
                '</div>',
                user.name or 'No name',
                user.address,
                contrib.contribution_type.name,
                contrib.points,
                contrib.frozen_global_points,
                contrib.contribution_date.strftime('%Y-%m-%d %H:%M'),
                contrib.notes or 'No notes'
            )
        return '-'
    contribution_details.short_description = 'Full Contribution Details'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related(
            'contribution',
            'contribution__user',
            'contribution__contribution_type'
        )


@admin.register(Mission)
class MissionAdmin(BroadcastNotificationAdminMixin, admin.ModelAdmin):
    broadcast_event_slug = 'mission.published'
    broadcast_service = staticmethod(notification_services.broadcast_mission)
    broadcast_eligible = staticmethod(lambda obj: obj.is_active())
    broadcast_ineligible_reason = 'the mission is not active'
    list_display = (
        'id', 'name', 'contribution_type', 'get_status',
        'get_submission_usage', 'start_date', 'end_date', 'created_at',
    )
    list_filter = (ContributionTypeListFilter, 'start_date', 'end_date', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_editable = ()
    list_per_page = 25
    show_full_result_count = False
    show_facets = admin.ShowFacets.NEVER
    autocomplete_fields = ('contribution_type',)

    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'contribution_type')
        }),
        ('Details', {
            'fields': ('description',)
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date'),
            'description': 'Optional: Set dates to control when this mission is active'
        }),
        ('Submission Limit', {
            'fields': ('max_submissions', 'max_submissions_per_user'),
            'description': (
                'Optional: Limit total non-rejected, non-canceled submissions '
                'and per-user non-rejected, non-canceled submissions for '
                'this mission.'
            )
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('contribution_type').annotate(
            submission_count=coalesced_count(
                active_submission_count_subquery('mission_id')
            )
        ).order_by('-created_at', '-id')

    def get_status(self, obj):
        if obj.is_active():
            return format_html('<span style="color: {};">●</span> {}', 'green', 'Active')
        else:
            return format_html('<span style="color: {};">●</span> {}', 'red', 'Inactive')
    get_status.short_description = 'Status'

    def get_submission_usage(self, obj):
        count = obj.get_submission_count()
        if obj.max_submissions is None:
            return f'{count} / Unlimited'
        return f'{count} / {obj.max_submissions}'
    get_submission_usage.short_description = 'Submissions'


@admin.register(StartupRequest)
class StartupRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'get_status', 'order', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'description', 'short_description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_editable = ('order',)
    ordering = ('order', '-created_at')

    fieldsets = (
        (None, {
            'fields': ('id', 'title', 'is_active', 'order')
        }),
        ('Content', {
            'fields': ('short_description', 'description'),
            'description': 'Short description is shown in the listing. Full description supports Markdown.'
        }),
        ('Documents', {
            'fields': ('documents',),
            'description': 'JSON array of document objects: [{"title": "...", "url": "...", "type": "pdf|image"}]'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_status(self, obj):
        if obj.is_active:
            return format_html('<span style="color: {};">●</span> {}', 'green', 'Active')
        else:
            return format_html('<span style="color: {};">●</span> {}', 'red', 'Inactive')
    get_status.short_description = 'Status'


@admin.register(FeaturedContent)
class FeaturedContentAdmin(BroadcastNotificationAdminMixin, CloudinaryUploadMixin, admin.ModelAdmin):
    broadcast_event_slug = 'featured.published'
    broadcast_service = staticmethod(notification_services.broadcast_featured_content)
    broadcast_eligible = staticmethod(lambda obj: obj.status == 'active')
    broadcast_ineligible_reason = 'the featured content is not active'

    form = FeaturedContentAdminForm
    cloudinary_upload_fields = {
        'hero_image_url': {
            'public_id_field': 'hero_image_public_id',
            'folder': 'tally/featured',
        },
        'hero_image_url_tablet': {
            'public_id_field': 'hero_image_tablet_public_id',
            'folder': 'tally/featured',
        },
        'hero_image_url_mobile': {
            'public_id_field': 'hero_image_mobile_public_id',
            'folder': 'tally/featured',
        },
        'user_profile_image_url': {
            'public_id_field': 'user_profile_image_public_id',
            'folder': 'tally/featured/avatars',
        },
    }

    list_display = ('title', 'content_type', 'display_hero_placements', 'user', 'status', 'order', 'created_at')
    list_filter = ('content_type', 'status', 'created_at')
    search_fields = ('title', 'description', 'user__name', 'user__address')
    list_editable = ('order', 'status')
    raw_id_fields = ('user', 'contribution')
    readonly_fields = ('created_at', 'updated_at', 'hero_image_public_id',
                       'hero_image_tablet_public_id', 'hero_image_mobile_public_id',
                       'user_profile_image_public_id')
    ordering = ('order', '-created_at')

    fieldsets = (
        (None, {
            'fields': ('content_type', 'title', 'author', 'description', 'hero_placements', 'status', 'order')
        }),
        ('Relations', {
            'fields': ('user', 'contribution')
        }),
        ('Links & Media', {
            'fields': ('hero_image_url', 'hero_image_url_tablet', 'hero_image_url_mobile',
                       'user_profile_image_url', 'url'),
            'description': 'Upload images directly or paste Cloudinary URLs. Tablet/mobile hero images are optional — falls back to the main hero image.'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Hero placements')
    def display_hero_placements(self, obj):
        labels = dict(FeaturedContent.HERO_PLACEMENT_CHOICES)
        placements = obj.hero_placements or []
        return ', '.join(labels.get(placement, placement) for placement in placements) or '-'


@admin.register(Alert)
class AlertAdmin(BroadcastNotificationAdminMixin, admin.ModelAdmin):
    broadcast_event_slug = 'alert.published'
    broadcast_service = staticmethod(notification_services.broadcast_alert)
    broadcast_eligible = staticmethod(lambda obj: obj.is_active)
    broadcast_ineligible_reason = 'the alert is inactive'

    list_display = ('id', 'alert_type', 'text_preview', 'get_status', 'order', 'start_date', 'end_date', 'created_at')
    list_filter = ('alert_type', 'is_active', 'created_at')
    search_fields = ('text',)
    list_editable = ('order', 'alert_type')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('order', '-created_at')

    fieldsets = (
        ('Content', {
            'fields': ('id', 'alert_type', 'icon', 'text', 'is_active', 'order')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date'),
            'description': 'Optional: Set dates to control when this alert is visible'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def text_preview(self, obj):
        return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text
    text_preview.short_description = 'Text'

    def get_status(self, obj):
        from django.utils import timezone as tz
        from django.utils.safestring import mark_safe
        now = tz.now()
        if not obj.is_active:
            return mark_safe('<span style="color: gray;">●</span> Inactive')
        if obj.start_date and now < obj.start_date:
            return mark_safe('<span style="color: orange;">●</span> Scheduled')
        if obj.end_date and now > obj.end_date:
            return mark_safe('<span style="color: red;">●</span> Expired')
        return mark_safe('<span style="color: green;">●</span> Active')
    get_status.short_description = 'Status'
