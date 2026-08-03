from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html, format_html_join

from .models import CampaignLink, CampaignRedirectHit, MarketingCampaign, UserAcquisitionAttribution
from .services import campaign_report


class CampaignLinkInline(admin.TabularInline):
    model = CampaignLink
    extra = 1
    # Deleting a link cascades away its redirect-hit history; pause with
    # is_active instead.
    can_delete = False
    fields = (
        'role', 'alias', 'destination_path',
        'utm_source', 'utm_medium', 'utm_content', 'utm_term',
        'is_active', 'link_url',
    )
    readonly_fields = ('link_url',)

    @admin.display(description='Public URL')
    def link_url(self, obj):
        return obj.public_url if obj.pk else ''


@admin.register(MarketingCampaign)
class MarketingCampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'tracking_key', 'is_active', 'starts_at', 'ends_at', 'link_count')
    list_filter = ('is_active',)
    search_fields = ('name', 'tracking_key')
    inlines = [CampaignLinkInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(link_count=Count('links', distinct=True))

    @admin.display(ordering='link_count', description='Links')
    def link_count(self, obj):
        return obj.link_count

    def get_readonly_fields(self, request, obj=None):
        # Published tracking keys are immutable: clone the campaign instead of
        # rewriting history.
        return ('tracking_key', 'performance') if obj else ('performance',)

    @admin.display(description='Performance (Portal DB)')
    def performance(self, obj):
        if not obj or not obj.pk:
            return 'Available after the campaign is saved.'
        report = campaign_report(obj)
        activations = report['activations']
        rows = [
            ('Redirect hits (human)', report['redirect_hits_human']),
            ('Redirect hits (probable bots)', report['redirect_hits_bot']),
            ('Wallet connects (attributed pending signups)', report['wallet_connects']),
            ('Registered users', report['signups']),
            ('Activated builders (first builder submission)', activations['builder']),
            ('Activated validators (joined waitlist)', activations['validator']),
            ('Activated community (flagged task completed)', activations['community']),
        ]
        body = format_html_join(
            '',
            '<tr><th style="text-align:left;padding:2px 12px 2px 0;">{}</th><td>{}</td></tr>',
            rows,
        )
        return format_html(
            '<table>{}</table>'
            '<p style="color:#666;">Source: Portal DB. Hits are redirect requests, not unique '
            'visitors; use GA for session-level traffic.</p>',
            body,
        )

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, CampaignLink) and not instance.created_by_id:
                instance.created_by = request.user
            instance.save()
        formset.save_m2m()


@admin.register(CampaignLink)
class CampaignLinkAdmin(admin.ModelAdmin):
    list_display = (
        'alias', 'role', 'campaign', 'utm_source', 'utm_medium',
        'is_active', 'human_hits', 'bot_hits', 'signups', 'public_url',
    )
    list_filter = ('role', 'is_active', 'campaign')
    search_fields = ('alias', 'campaign__name', 'campaign__tracking_key', 'utm_source', 'utm_medium')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            human_hit_count=Count('hits', filter=Q(hits__is_probable_bot=False), distinct=True),
            bot_hit_count=Count('hits', filter=Q(hits__is_probable_bot=True), distinct=True),
            signup_count=Count('acquisitions', distinct=True),
        )

    @admin.display(ordering='human_hit_count', description='Hits (human)')
    def human_hits(self, obj):
        return obj.human_hit_count

    @admin.display(ordering='bot_hit_count', description='Hits (bots)')
    def bot_hits(self, obj):
        return obj.bot_hit_count

    @admin.display(ordering='signup_count', description='Signups')
    def signups(self, obj):
        return obj.signup_count

    def get_readonly_fields(self, request, obj=None):
        base = ('tracking_id', 'redirect_preview')
        # Campaign, role, and alias define the published link's identity; once
        # it is live they must not silently change meaning (moving a link
        # between campaigns would also move its hit history). Create a new
        # link instead.
        return base + ('campaign', 'role', 'alias') if obj else base

    def has_delete_permission(self, request, obj=None):
        # Deleting a link cascades away its redirect-hit history; pause with
        # is_active instead. Superuser escape hatch only.
        return request.user.is_superuser

    @admin.display(description='Redirect target (preview)')
    def redirect_preview(self, obj):
        if not obj or not obj.pk:
            return 'Available after the link is saved.'
        return format_html(
            'Public URL: <a href="{0}">{0}</a><br>Redirects to: {1}', obj.public_url, obj.redirect_target,
        )

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CampaignRedirectHit)
class CampaignRedirectHitAdmin(admin.ModelAdmin):
    list_display = (
        'campaign_link', 'occurred_at', 'referrer_host',
        'user_agent_family', 'device_category', 'is_probable_bot',
    )
    list_filter = ('is_probable_bot', 'device_category')
    date_hierarchy = 'occurred_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Escape hatch for manual cleanup; routine retention goes through the
        # purge_campaign_hits management command.
        return request.user.is_superuser


@admin.register(UserAcquisitionAttribution)
class UserAcquisitionAttributionAdmin(admin.ModelAdmin):
    list_display = ('user', 'campaign_key', 'source', 'medium', 'link_role', 'registered_at')
    list_filter = ('link_role', 'campaign_key')
    search_fields = ('user__email', 'user__name', 'campaign_key', 'link_tracking_id')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # Acquisition facts are immutable.
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
