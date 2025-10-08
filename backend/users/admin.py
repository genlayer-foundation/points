from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib import messages

from .models import User
from contributions.models import Contribution
from validators.admin import ValidatorInline
from builders.admin import BuilderInline
from stewards.admin import StewardInline
from validators.models import Validator
from builders.models import Builder
from stewards.models import Steward


class ContributionInline(admin.TabularInline):
    model = Contribution
    extra = 0  # Don't show empty rows
    fields = ('contribution_type', 'points', 'contribution_date', 'evidence_link', 'multiplier_at_creation', 'frozen_global_points')
    readonly_fields = ('multiplier_at_creation', 'frozen_global_points', 'evidence_link')
    can_delete = True
    show_change_link = True
    verbose_name = "Contribution"
    verbose_name_plural = "Contributions"
    ordering = ('-created_at', '-contribution_date')  # Most recent contributions first, based on creation date
    
    def evidence_link(self, obj):
        """Display a link to add/edit evidence for this contribution."""
        from django.utils.html import format_html
        from django.urls import reverse
        
        if obj and obj.id:
            change_url = reverse('admin:contributions_contribution_change', args=[obj.id])
            count = obj.evidence_items.count()
            if count > 0:
                return format_html('<a href="{}#evidence_items-group">View/Edit {} Evidence Item{}</a>', 
                               change_url, count, 's' if count > 1 else '')
            else:
                return format_html('<a href="{}#evidence_items-group">Add Evidence</a>', change_url)
        return '-'
    evidence_link.short_description = 'Evidence'


# ValidatorInline removed - now in validators app


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'name', 'is_staff', 'is_active', 'visible', 'address', 'is_email_verified')
    list_filter = ('is_staff', 'is_active', 'visible', 'is_email_verified')
    search_fields = ('email', 'name', 'address', 'referral_code', 'twitter_handle', 'discord_handle', 'telegram_handle')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password', 'is_email_verified')}),
        (_('Personal info'), {'fields': ('name', 'address', 'description')}),
        (_('Profile Images'), {'fields': ('profile_image_url', 'banner_image_url', 'profile_image_public_id', 'banner_image_public_id')}),
        (_('Contact & Social'), {'fields': ('website', 'twitter_handle', 'discord_handle', 'telegram_handle', 'linkedin_handle')}),
        (_('GitHub Integration'), {'fields': ('github_username', 'github_user_id', 'github_linked_at')}),
        (_('Referral System'), {'fields': ('referral_code', 'referred_by')}),
        (_('Visibility'), {'fields': ('visible',)}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at', 'profile_image_public_id', 'banner_image_public_id', 'referral_code', 'github_user_id', 'github_linked_at')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'name', 'address', 'visible'),
        }),
    )
    
    inlines = [ContributionInline, ValidatorInline, BuilderInline, StewardInline]
    actions = ['set_as_builder', 'set_as_validator', 'set_as_steward', 'disconnect_github']
    
    def set_as_builder(self, request, queryset):
        """Action to set selected users as builders."""
        count = 0
        for user in queryset:
            # Check if already a builder
            if hasattr(user, 'builder'):
                self.message_user(request, f"{user.email} is already a builder.", level=messages.WARNING)
                continue
            
            # Create builder profile
            Builder.objects.create(user=user)
            count += 1
        
        if count > 0:
            self.message_user(request, f"Successfully set {count} user(s) as builder(s).", level=messages.SUCCESS)
    set_as_builder.short_description = "Set selected users as builders"
    
    def set_as_validator(self, request, queryset):
        """Action to set selected users as validators and track graduation if from waitlist."""
        from django.utils import timezone
        from contributions.models import Contribution, ContributionType
        from leaderboard.models import LeaderboardEntry
        
        count = 0
        graduated_count = 0
        
        for user in queryset:
            # Check if already a validator
            if hasattr(user, 'validator'):
                self.message_user(request, f"{user.email} is already a validator.", level=messages.WARNING)
                continue
            
            # Check if user has validator-waitlist badge
            has_waitlist = False
            current_points = 0
            
            try:
                waitlist_type = ContributionType.objects.get(slug='validator-waitlist')
                has_waitlist = Contribution.objects.filter(
                    user=user,
                    contribution_type=waitlist_type
                ).exists()
                
                # Get current total points from validator-waitlist leaderboard
                leaderboard_entry = LeaderboardEntry.objects.filter(
                    user=user,
                    type='validator-waitlist'
                ).first()
                
                if leaderboard_entry:
                    current_points = leaderboard_entry.total_points
            except (ContributionType.DoesNotExist, LeaderboardEntry.DoesNotExist):
                pass
            
            # Create validator profile with graduation info if from waitlist
            validator = Validator.objects.create(
                user=user,
            )
            if has_waitlist:
                graduated_count += 1
                self.message_user(
                    request, 
                    f"{user.email} graduated from waitlist with {current_points} points.", 
                    level=messages.SUCCESS
                )
            
            # Add validator badge contribution
            try:
                validator_type = ContributionType.objects.get(slug='validator')
                Contribution.objects.create(
                    user=user,
                    contribution_type=validator_type,
                    points=validator_type.min_points or 200,
                    contribution_date=timezone.now(),
                    notes="Validator badge awarded"
                )
            except ContributionType.DoesNotExist:
                pass
            
            count += 1
        
        if count > 0:
            msg = f"Successfully set {count} user(s) as validator(s)."
            if graduated_count > 0:
                msg += f" {graduated_count} graduated from waitlist."
            self.message_user(request, msg, level=messages.SUCCESS)
    set_as_validator.short_description = "Set selected users as validators"
    
    def set_as_steward(self, request, queryset):
        """Action to set selected users as stewards."""
        count = 0
        for user in queryset:
            # Check if already a steward
            if hasattr(user, 'steward'):
                self.message_user(request, f"{user.email} is already a steward.", level=messages.WARNING)
                continue

            # Create steward profile
            Steward.objects.create(user=user)
            count += 1

        if count > 0:
            self.message_user(request, f"Successfully set {count} user(s) as steward(s).", level=messages.SUCCESS)
    set_as_steward.short_description = "Set selected users as stewards"

    def disconnect_github(self, request, queryset):
        """Action to disconnect GitHub accounts from selected users."""
        count = 0
        for user in queryset:
            if not user.github_username:
                self.message_user(request, f"{user.email} doesn't have a GitHub account linked.", level=messages.WARNING)
                continue

            # Clear all GitHub fields
            user.github_username = ""
            user.github_user_id = ""
            user.github_access_token = ""
            user.github_linked_at = None
            user.save()
            count += 1

        if count > 0:
            self.message_user(request, f"Successfully disconnected GitHub from {count} user(s).", level=messages.SUCCESS)
    disconnect_github.short_description = "Disconnect GitHub accounts from selected users"
