from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from utils.models import BaseModel
from contributions.models import ContributionType, Contribution


class GlobalLeaderboardMultiplier(BaseModel):
    """
    Tracks the history of multiplier values over time for contribution types.
    
    Each contribution type can have multiple multiplier values over time,
    and this model keeps track of when each value became active.
    """
    contribution_type = models.ForeignKey(
        ContributionType,
        on_delete=models.CASCADE,
        related_name='multipliers'
    )
    multiplier_value = models.DecimalField(max_digits=10, decimal_places=2, default=1.0)
    valid_from = models.DateTimeField()
    description = models.CharField(max_length=255, blank=True, help_text="Reason for this multiplier value")
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-valid_from']
        get_latest_by = 'valid_from'
    
    def __str__(self):
        return f"{self.contribution_type.name}: {self.multiplier_value}x (from {self.valid_from.strftime('%Y-%m-%d %H:%M')})"
    
    def clean(self):
        """Validate the multiplier data."""
        super().clean()
        
        # Ensure multiplier_value is positive
        if self.multiplier_value <= 0:
            raise ValidationError("Multiplier value must be positive")
            
    def save(self, *args, **kwargs):
        """
        Override save to validate the multiplier.
        """
        self.clean()
        super().save(*args, **kwargs)
    
    @classmethod
    def get_current_multiplier_value(cls, contribution_type):
        """
        Get the current multiplier value for this contribution type.
        Returns the value of the most recent period, or 1.0 if none exists.
        """
        latest_multiplier = cls.objects.filter(
            contribution_type=contribution_type
        ).order_by('-valid_from').first()
        
        if latest_multiplier:
            return latest_multiplier.multiplier_value
        return 1.0
    
    @classmethod
    def get_active_for_type(cls, contribution_type, at_date=None):
        """
        Get the active multiplier for a given contribution type at a specific date.
        If no date is provided, uses the current date/time.
        
        Returns a tuple of (multiplier_obj, multiplier_value)
        Raises DoesNotExist if no multiplier exists for the contribution type or
        if no period exists for the given date.
        """
        at_date = at_date or timezone.now()
        
        # Find the multiplier that is valid at the given date
        # (the most recent multiplier that started before or at the given date)
        multiplier = cls.objects.filter(
            contribution_type=contribution_type,
            valid_from__lte=at_date
        ).order_by('-valid_from').first()
            
        if not multiplier:
            raise cls.DoesNotExist(
                f"No multiplier exists for contribution type '{contribution_type}' at {at_date}"
            )
            
        return multiplier, multiplier.multiplier_value


class LeaderboardEntry(BaseModel):
    """
    Represents a user's position on the leaderboard.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='leaderboard_entry'
    )
    total_points = models.PositiveIntegerField(default=0)
    rank = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-total_points', 'user__name']
        verbose_name_plural = 'Leaderboard entries'
    
    def __str__(self):
        return f"{self.user} - {self.total_points} points - Rank: {self.rank or 'Not ranked'}"


# Signals to update leaderboard entries
@receiver(post_save, sender=GlobalLeaderboardMultiplier)
def log_multiplier_creation(sender, instance, created, **kwargs):
    """
    When a new multiplier is created, log it for debugging purposes.
    """
    if created:
        print(f"New global multiplier: {instance.contribution_type.name} - "
              f"{instance.multiplier_value}x valid from {instance.valid_from.strftime('%Y-%m-%d %H:%M')}")


@receiver(post_save, sender=Contribution)
def update_leaderboard_on_contribution(sender, instance, created, **kwargs):
    """
    When a contribution is saved, update the leaderboard entry.
    
    Note: We don't need to recalculate frozen_global_points here as it's 
    handled in the Contribution.save() method using the multiplier_at_creation value.
    """
    # Only update if points have changed or it's a new contribution
    if created or kwargs.get('update_fields') is None or 'points' in kwargs.get('update_fields', []):
        # Log the contribution's point calculation
        contribution_date_str = instance.contribution_date.strftime('%Y-%m-%d %H:%M') if instance.contribution_date else "N/A"
        print(f"Contribution saved: {instance.points} points × {instance.multiplier_at_creation} = "
              f"{instance.frozen_global_points} global points (contribution date: {contribution_date_str})")
    
    # Update the user's leaderboard entry
    update_user_leaderboard_entry(instance.user)


def update_user_leaderboard_entry(user):
    """
    Update or create a leaderboard entry for a user based on their total frozen_global_points.
    """
    total_points = Contribution.objects.filter(user=user).values_list('frozen_global_points', flat=True)
    total_points = sum(total_points)
    
    # Update or create the leaderboard entry
    LeaderboardEntry.objects.update_or_create(
        user=user,
        defaults={'total_points': total_points}
    )
    
    # Recompute all ranks
    update_all_ranks()


def update_all_ranks():
    """
    Update the ranks for all leaderboard entries.
    """
    entries = LeaderboardEntry.objects.all().order_by('-total_points')
    rank = 1
    
    for i, entry in enumerate(entries):
        # If this entry has the same points as the previous one, give it the same rank
        if i > 0 and entry.total_points == entries[i-1].total_points:
            entry.rank = entries[i-1].rank
        else:
            entry.rank = rank
        
        entry.save(update_fields=['rank'])
        
        # Only increment rank if the next entry will have a different rank
        if i < len(entries) - 1 and entry.total_points != entries[i+1].total_points:
            rank += 1
