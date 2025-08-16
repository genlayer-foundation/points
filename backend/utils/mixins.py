from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
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
    
    def check_node_version_and_contribute(self):
        """
        Check if the node version has been updated compared to the target and
        create a contribution if it matches or exceeds the target.
        This should be called after save in the implementing model.
        """
        from contributions.node_upgrade.models import TargetNodeVersion
        from contributions.models import Contribution, ContributionType
        
        # Only proceed if we have a node version
        if not self.node_version:
            return
        
        # Get the active target version
        target = TargetNodeVersion.get_active()
        if not target:
            return
        
        # Check if version matches or is higher
        if not self.version_matches_or_higher(target.version):
            return
        
        # Check if user already has a contribution for this target
        existing_contribution = Contribution.objects.filter(
            user=self.user,
            contribution_type__slug='node-upgrade',
            meta_data__target_version_id=target.id
        ).first()
        
        if existing_contribution:
            return  # Already recorded
        
        # Get the node upgrade contribution type
        try:
            contribution_type = ContributionType.objects.get(slug='node-upgrade')
        except ContributionType.DoesNotExist:
            print(f"Node upgrade contribution type not found")
            return
        
        # Calculate points based on how quickly the upgrade was done
        days_since_target = (timezone.now() - target.created_at).days
        if days_since_target <= 0:
            points = 4  # Same day
        elif days_since_target == 1:
            points = 3  # Next day
        elif days_since_target == 2:
            points = 2  # Day after
        else:
            points = 1  # Later
        
        # Create the contribution
        Contribution.objects.create(
            user=self.user,
            contribution_type=contribution_type,
            points=points,
            meta_data={
                'target_version_id': target.id,
                'target_version': target.version,
                'node_version': self.node_version,
                'days_to_upgrade': days_since_target
            },
            url=f"Node upgraded to {self.node_version}",
            description=f"Upgraded node to version {self.node_version} meeting target {target.version}"
        )