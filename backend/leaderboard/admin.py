from django.contrib import admin
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.core.management import call_command
from .models import LeaderboardEntry, GlobalLeaderboardMultiplier
from contributions.models import Category, Contribution
from users.models import User


@admin.register(LeaderboardEntry)
class LeaderboardEntryAdmin(admin.ModelAdmin):
    list_display = ('rank', 'user', 'category', 'total_points', 'created_at', 'updated_at')
    list_filter = ('category', 'rank', 'created_at')
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
                # Calculate and create global leaderboard entry
                global_points = Contribution.objects.filter(
                    user=user
                ).values_list('frozen_global_points', flat=True)
                global_total = sum(global_points)
                
                if global_total > 0:
                    LeaderboardEntry.objects.create(
                        user=user,
                        category=None,  # Global
                        total_points=global_total
                    )
                    created_count += 1
                
                # Create category-specific leaderboard entries
                categories = Category.objects.all()
                for category in categories:
                    cat_contributions = Contribution.objects.filter(
                        user=user,
                        contribution_type__category=category
                    )
                    cat_points = sum(c.frozen_global_points for c in cat_contributions)
                    
                    if cat_points > 0:
                        LeaderboardEntry.objects.create(
                            user=user,
                            category=category,
                            total_points=cat_points
                        )
                        created_count += 1
            
            # Update all ranks (global and per-category)
            # Update global leaderboard ranks
            LeaderboardEntry.update_category_ranks(category=None)
            
            # Update each category's leaderboard ranks
            for category in Category.objects.all():
                LeaderboardEntry.update_category_ranks(category=category)
            
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
    
    recreate_all_leaderboards.short_description = "Recreate all leaderboards (global and categories)"
    
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
