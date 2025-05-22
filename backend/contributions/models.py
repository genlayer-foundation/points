from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver
from utils.models import BaseModel
import decimal


class ContributionType(BaseModel):
    """
    Represents different types of contributions that participants can make.
    Examples: Node Runner, Uptime, Asimov, Blog Post, etc.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Contribution(BaseModel):
    """
    Represents a specific contribution made by a user.
    Links user with a contribution type and records points.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='contributions'
    )
    contribution_type = models.ForeignKey(
        ContributionType, 
        on_delete=models.CASCADE, 
        related_name='contributions'
    )
    points = models.PositiveIntegerField(default=0)
    frozen_global_points = models.PositiveIntegerField(default=0)
    multiplier_at_creation = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    contribution_date = models.DateTimeField(null=True, blank=True, help_text="Date when the contribution was made. Defaults to creation time if not specified.")
    evidence_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user} - {self.contribution_type} - {self.points} points"
    
    def clean(self):
        """
        Validate that there is an active multiplier for this contribution type
        and that the user is visible.
        """
        super().clean()
        
        # Import here to avoid circular imports
        from django.utils import timezone
        from leaderboard.models import GlobalLeaderboardMultiplier
        
        # Check if the user is visible
        if not self.user.visible:
            raise ValidationError(
                f"Cannot add contributions for user '{self.user.email}' as they are marked as not visible. "
                "Only visible users can have contributions."
            )
        
        # Set contribution_date to now if not provided
        if not self.contribution_date:
            self.contribution_date = timezone.now()
        
        try:
            # Check if there's an active multiplier for this contribution type on the contribution date
            # The method returns a tuple of (multiplier_obj, multiplier_value)
            _, multiplier_value = GlobalLeaderboardMultiplier.get_active_for_type(
                self.contribution_type, 
                at_date=self.contribution_date
            )
            self.multiplier_at_creation = multiplier_value
        except GlobalLeaderboardMultiplier.DoesNotExist as e:
            raise ValidationError(
                f"No active multiplier exists for contribution type '{self.contribution_type}' "
                f"on {self.contribution_date.strftime('%Y-%m-%d %H:%M')}. "
                "Please set a multiplier that covers this date before adding contributions."
            ) from e
    
    def save(self, *args, **kwargs):
        """
        Override save to validate and calculate frozen_global_points.
        """
        from django.utils import timezone
        
        # Set contribution_date if not set yet
        if not self.contribution_date:
            self.contribution_date = timezone.now()
            
        # Only run validation on new contributions
        if not self.pk:
            self.clean()
            
            # Calculate frozen_global_points
            try:
                if self.multiplier_at_creation:
                    self.frozen_global_points = int(self.points * float(self.multiplier_at_creation))
            except (decimal.InvalidOperation, TypeError, ValueError):
                # Handle corrupted data by resetting the multiplier
                self.multiplier_at_creation = 1.0
                self.frozen_global_points = self.points
                
        super().save(*args, **kwargs)


# Signal to validate multiplier_at_creation before save
@receiver(pre_save, sender=Contribution)
def validate_multiplier_at_creation(sender, instance, **kwargs):
    """
    Signal to validate multiplier_at_creation before saving a Contribution.
    This helps prevent corrupted decimal values.
    """
    if instance.multiplier_at_creation:
        try:
            # Test if we can convert the decimal value
            float(instance.multiplier_at_creation)
        except (decimal.InvalidOperation, TypeError, ValueError):
            # If conversion fails, reset the multiplier to 1.0
            print(f"WARNING: Fixing corrupted multiplier_at_creation value for contribution {instance.id}")
            instance.multiplier_at_creation = 1.0
            instance.frozen_global_points = instance.points
