from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from utils.models import BaseModel


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
        Validate that there is an active multiplier for this contribution type.
        """
        super().clean()
        
        # Import here to avoid circular imports
        from django.utils import timezone
        from leaderboard.models import GlobalLeaderboardMultiplier
        
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
            if self.multiplier_at_creation:
                self.frozen_global_points = int(self.points * float(self.multiplier_at_creation))
            
        super().save(*args, **kwargs)
