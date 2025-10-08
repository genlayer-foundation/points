from django.contrib import admin
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.core.management import call_command
from .models import LeaderboardEntry, GlobalLeaderboardMultiplier, ReferralPoints
from contributions.models import Category, Contribution
from users.models import User


@admin.register(LeaderboardEntry)
class LeaderboardEntryAdmin(admin.ModelAdmin):
    list_display = ('rank', 'user', 'type', 'total_points', 'created_at', 'updated_at')
    list_filter = ('type', 'rank', 'created_at')
    search_fields = ('user__email', 'user__name')
    readonly_fields = ('total_points', 'rank', 'created_at', 'updated_at')
    ordering = ('rank', '-total_points')
    actions = ['recreate_all_leaderboards']
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('update-leaderboard/', self.admin_site.admin_view(self.update_leaderboard_view), name='update_leaderboard'),
        ]
        return custom_urls + urls
    
    def has_add_permission(self, request):
        # Don't allow manual creation of leaderboard entries
        return False
    
    def recreate_all_leaderboards(self, request, queryset):
        """
        Admin action to recreate all leaderboard entries (global and category-specific).
        This will:
        1. Delete all existing leaderboard entries
        2. Recreate entries based on current contributions
        3. Update all ranks
        """
        try:
            # Delete all existing leaderboard entries
            deleted_count = LeaderboardEntry.objects.all().delete()[0]
            
            # Get all users who have contributions
            users_with_contributions = User.objects.filter(
                contributions__isnull=False
            ).distinct()
            
            # Counter for created entries
            created_count = 0
            
            # For each user, create their leaderboard entries
            for user in users_with_contributions:
                # Calculate user's total points
                total_points = sum(Contribution.objects.filter(
                    user=user
                ).values_list('frozen_global_points', flat=True))
                
                if total_points > 0:
                    # Determine which leaderboards this user should be on
                    user_leaderboards = LeaderboardEntry.determine_user_leaderboards(user)
                    
                    # Create entries for each qualified leaderboard
                    for leaderboard_type in user_leaderboards:
                        LeaderboardEntry.objects.create(
                            user=user,
                            type=leaderboard_type,
                            total_points=total_points
                        )
                        created_count += 1
            
            # Update all ranks for each leaderboard type
            for leaderboard_type, _ in LeaderboardEntry.LEADERBOARD_TYPES:
                LeaderboardEntry.update_leaderboard_ranks(leaderboard_type)
            
            # Show success message
            self.message_user(
                request,
                f"Successfully recreated leaderboards. Deleted {deleted_count} old entries, created {created_count} new entries.",
                messages.SUCCESS
            )
            
        except Exception as e:
            self.message_user(
                request,
                f"Error recreating leaderboards: {str(e)}",
                messages.ERROR
            )
    
    recreate_all_leaderboards.short_description = "Recreate all leaderboards"
    
    def update_leaderboard_view(self, request):
        """View for updating the leaderboard using the management command."""
        if request.method == 'POST':
            try:
                # Run the update_leaderboard management command
                call_command('update_leaderboard')
                messages.success(request, 'Leaderboard updated successfully! All contribution multipliers and points have been recalculated.')
            except Exception as e:
                messages.error(request, f'Error updating leaderboard: {str(e)}')
            
            return HttpResponseRedirect(reverse('admin:leaderboard_leaderboardentry_changelist'))
        
        context = {
            'title': 'Update Leaderboard',
            'opts': self.model._meta,
            'has_change_permission': request.user.has_perm('leaderboard.change_leaderboardentry'),
        }
        return render(request, 'admin/leaderboard/update_leaderboard.html', context)


@admin.register(ReferralPoints)
class ReferralPointsAdmin(admin.ModelAdmin):
    list_display = ['user', 'builder_points', 'validator_points', 'total_referral_points']
    search_fields = ['user__email', 'user__name']
    readonly_fields = ['user', 'builder_points', 'validator_points']
    actions = ['recalculate_referral_points']

    def total_referral_points(self, obj):
        """Display total referral points (builder + validator)"""
        return obj.builder_points + obj.validator_points
    total_referral_points.short_description = 'Total Points'

    def has_add_permission(self, request):
        # Don't allow manual creation
        return False

    def has_delete_permission(self, request, obj=None):
        # Allow deletion for cleanup
        return True

    def recalculate_referral_points(self, request, queryset):
        """
        Admin action to recalculate all referral points from scratch.
        This will:
        1. Delete all existing referral points
        2. Recalculate based on actual contribution data
        """
        try:
            from .models import recalculate_referrer_points
            from django.db import transaction

            with transaction.atomic():
                # Delete all existing referral points
                deleted_count = ReferralPoints.objects.all().count()
                ReferralPoints.objects.all().delete()

                # Get all users who have referred at least one person
                referrers = User.objects.filter(referrals__isnull=False).distinct()
                updated_count = 0

                # Recalculate for each referrer
                for referrer in referrers:
                    recalculate_referrer_points(referrer)
                    updated_count += 1

                # Show success message
                self.message_user(
                    request,
                    f"Successfully recalculated referral points. Deleted {deleted_count} old records, recalculated {updated_count} referrers.",
                    messages.SUCCESS
                )

        except Exception as e:
            self.message_user(
                request,
                f"Error recalculating referral points: {str(e)}",
                messages.ERROR
            )

    recalculate_referral_points.short_description = "Recalculate all referral points from scratch"
