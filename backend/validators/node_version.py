"""
Node version tracking and points calculation for validators.
"""
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from packaging import version
import re


class NodeVersionMixin(models.Model):
    """
    Abstract model mixin for handling node version functionality.
    Can be used by any profile model that needs to track node versions.
    """
    node_version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Current node version (e.g., 0.3.9)"
    )
    
    class Meta:
        abstract = True
    
    def clean(self):
        """Validate the node version format."""
        super().clean()
        
        if self.node_version:
            # Basic semantic versioning check
            pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9\-\.]+)?(\+[a-zA-Z0-9\-\.]+)?$'
            if not re.match(pattern, self.node_version):
                raise ValidationError({
                    'node_version': 'Node version must follow semantic versioning (e.g., 0.3.9, 1.2.3-beta.1)'
                })
    
    def version_matches_or_higher(self, target_version):
        """
        Check if this node's version matches or is higher than the target version.
        Uses semantic versioning comparison.
        """
        if not self.node_version or not target_version:
            return False
        
        try:
            # Parse versions for comparison
            current = version.parse(self.node_version)
            target = version.parse(target_version)
            
            # Compare versions
            return current >= target
        except Exception as e:
            # If parsing fails, fall back to string comparison
            print(f"Version parsing error: {e}")
            return self.node_version >= target_version
    
    def save(self, *args, **kwargs):
        """
        Override save to create SubmittedContribution with calculated points based on early upgrade bonus.
        """
        # Store the old version before saving
        old_version = None
        is_new = not self.pk
        if self.pk:
            try:
                old_obj = self.__class__.objects.get(pk=self.pk)
                old_version = old_obj.node_version
            except self.__class__.DoesNotExist:
                pass
        
        # Save the object first
        super().save(*args, **kwargs)
        
        # Check if version changed
        if (is_new and self.node_version) or (old_version != self.node_version and self.node_version):
            # Only create submission if user is visible
            if self.user.visible:
                from contributions.node_upgrade.models import TargetNodeVersion
                from contributions.models import SubmittedContribution, ContributionType, Contribution
                
                # Get active target
                target = TargetNodeVersion.get_active()
                if target and self.version_matches_or_higher(target.version):
                    # Check if contribution already exists for this target
                    contribution_type = ContributionType.objects.filter(slug='node-upgrade').first()
                    
                    if contribution_type:
                        # Check for existing submission or contribution with this target version in notes
                        existing_contribution = Contribution.objects.filter(
                            user=self.user,
                            contribution_type=contribution_type,
                            notes__contains=f"version {target.version}"
                        ).exists()
                        
                        existing_submission = SubmittedContribution.objects.filter(
                            user=self.user,
                            contribution_type=contribution_type,
                            state__in=['pending', 'accepted'],
                            notes__contains=f"version {target.version}"
                        ).exists()
                        
                        if not existing_contribution and not existing_submission:
                            # Calculate points based on early upgrade bonus only
                            points = calculate_early_upgrade_bonus(target.target_date, timezone.now())
                            
                            # Create the submitted contribution with suggested points
                            submission = SubmittedContribution.objects.create(
                                user=self.user,
                                contribution_type=contribution_type,
                                suggested_points=points,
                                contribution_date=timezone.now(),
                                notes=f"Automatic submission for node upgrade to version {target.version}",
                                state='pending'
                            )


def calculate_early_upgrade_bonus(target_availability_date, upgrade_date):
    """
    Calculate points for early adoption of a new target version.
    
    Args:
        target_availability_date: When the target version became available for upgrade
        upgrade_date: When the validator upgraded
        
    Returns:
        int: Points (4 for same day as availability, 3 for day 1, 2 for day 2, 1 for day 3+)
    """
    if not target_availability_date or not upgrade_date:
        return 1  # Minimum points if dates are missing
    
    days_elapsed = (upgrade_date - target_availability_date).days
    
    if days_elapsed <= 0:
        return 4  # Same day upgrade
    elif days_elapsed == 1:
        return 3
    elif days_elapsed == 2:
        return 2
    else:
        return 1  # Minimum points