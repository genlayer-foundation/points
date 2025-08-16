from django.db import models
from django.conf import settings
from django.utils import timezone
from utils.models import BaseModel
from utils.mixins import NodeVersionMixin


class Validator(NodeVersionMixin, BaseModel):
    """
    Represents a validator with their node version information.
    One-to-one relationship with User.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='validator'
    )
    # node_version field is inherited from NodeVersionMixin
    
    def __str__(self):
        return f"{self.user.email} - Node: {self.node_version or 'Not set'}"
    
    # Methods clean_version and version_matches_or_higher are inherited from NodeVersionMixin
    
    def save(self, *args, **kwargs):
        """
        Override save to check for version match with target and create contribution.
        """
        # Store the old version before saving
        old_version = None
        if self.pk:
            try:
                old_validator = Validator.objects.get(pk=self.pk)
                old_version = old_validator.node_version
            except Validator.DoesNotExist:
                pass
        
        # Save the validator first
        super().save(*args, **kwargs)
        
        # Check if version changed and matches target
        # Only create contribution if user is visible
        if old_version != self.node_version and self.node_version and self.user.visible:
            from contributions.node_upgrade.models import TargetNodeVersion
            from contributions.models import Contribution, ContributionType, Evidence
            
            # Get active target
            target = TargetNodeVersion.get_active()
            if target and self.version_matches_or_higher(target.version):
                # Check if contribution already exists for this target
                contribution_type = ContributionType.objects.filter(slug='node-upgrade').first()
                
                if contribution_type:
                    # Check for existing contribution with this target version as evidence
                    existing = Contribution.objects.filter(
                        user=self.user,
                        contribution_type=contribution_type
                    ).filter(
                        evidence_items__description__contains=f"Target version: {target.version}"
                    ).exists()
                    
                    if not existing:
                        # Calculate points based on days elapsed
                        days_elapsed = (timezone.now() - target.created_at).days
                        if days_elapsed <= 0:
                            points = 4
                        elif days_elapsed == 1:
                            points = 3
                        elif days_elapsed == 2:
                            points = 2
                        else:
                            points = 1
                        
                        # Create the contribution
                        contribution = Contribution.objects.create(
                            user=self.user,
                            contribution_type=contribution_type,
                            points=points,
                            contribution_date=timezone.now(),
                            notes=f"Automatic submission for node upgrade to version {target.version}"
                        )
                        
                        # Add evidence
                        Evidence.objects.create(
                            contribution=contribution,
                            description=f"Target version: {target.version}\nUpgraded on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\nDays elapsed: {days_elapsed}"
                        )