"""
Node version tracking and points calculation for validators.
"""
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from packaging import version
import re

from tally.middleware.logging_utils import get_app_logger

logger = get_app_logger('validators')


class NodeVersionMixin(models.Model):
    """
    Abstract model mixin for handling node version functionality.
    Tracks node versions per network (asimov, bradbury).
    """
    node_version_asimov = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Current node version for Asimov network (e.g., 0.3.9)"
    )
    node_version_bradbury = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Current node version for Bradbury network (e.g., 0.3.9)"
    )

    class Meta:
        abstract = True

    def clean(self):
        """Validate the node version format for both networks."""
        super().clean()

        pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9\-\.]+)?(\+[a-zA-Z0-9\-\.]+)?$'

        if self.node_version_asimov:
            if not re.match(pattern, self.node_version_asimov):
                raise ValidationError({
                    'node_version_asimov': 'Node version must follow semantic versioning (e.g., 0.3.9, 1.2.3-beta.1)'
                })

        if self.node_version_bradbury:
            if not re.match(pattern, self.node_version_bradbury):
                raise ValidationError({
                    'node_version_bradbury': 'Node version must follow semantic versioning (e.g., 0.3.9, 1.2.3-beta.1)'
                })

    @staticmethod
    def _compare_versions(node_version, target_version):
        """
        Check if node_version matches or is higher than target_version.
        Uses semantic versioning comparison.
        """
        if not node_version or not target_version:
            return False

        try:
            current = version.parse(node_version)
            target = version.parse(target_version)
            return current >= target
        except Exception as e:
            logger.warning(f"Version parsing error: {e}")
            return node_version >= target_version

    def version_matches_or_higher(self, target_version, node_version=None):
        """
        Check if the given (or asimov) node version matches or is higher than the target version.
        If node_version is provided, uses that directly. Otherwise uses node_version_asimov.
        """
        nv = node_version if node_version is not None else self.node_version_asimov
        return self._compare_versions(nv, target_version)

    def save(self, *args, **kwargs):
        """
        Override save to create SubmittedContribution with calculated points based on early upgrade bonus.
        Checks each network independently.
        """
        # Store old versions before saving
        old_version_asimov = None
        old_version_bradbury = None
        is_new = not self.pk
        if self.pk:
            try:
                old_obj = self.__class__.objects.get(pk=self.pk)
                old_version_asimov = old_obj.node_version_asimov
                old_version_bradbury = old_obj.node_version_bradbury
            except self.__class__.DoesNotExist:
                pass

        # Save the object first
        super().save(*args, **kwargs)

        # Only create submissions if user is visible
        if not self.user.visible:
            return

        # Check each network for version changes
        networks = [
            ('asimov', self.node_version_asimov, old_version_asimov),
            ('bradbury', self.node_version_bradbury, old_version_bradbury),
        ]

        for network, new_version, old_version in networks:
            version_changed = (is_new and new_version) or (old_version != new_version and new_version)
            if not version_changed:
                continue

            self._create_upgrade_submission(network, new_version)

    def _create_upgrade_submission(self, network, new_version):
        """Create a SubmittedContribution for a node upgrade on a given network."""
        from contributions.node_upgrade.models import TargetNodeVersion
        from contributions.models import SubmittedContribution, ContributionType, Contribution

        target = TargetNodeVersion.get_active(network=network)
        if not target or not self._compare_versions(new_version, target.version):
            return

        contribution_type = ContributionType.objects.filter(slug='node-upgrade').first()
        if not contribution_type:
            return

        # Include network in dedup key to allow separate submissions per network
        dedup_key = f"version {target.version} [{network}]"

        existing_contribution = Contribution.objects.filter(
            user=self.user,
            contribution_type=contribution_type,
            notes__contains=dedup_key
        ).exists()

        existing_submission = SubmittedContribution.objects.filter(
            user=self.user,
            contribution_type=contribution_type,
            state__in=['pending', 'accepted'],
            notes__contains=dedup_key
        ).exists()

        if not existing_contribution and not existing_submission:
            points = calculate_early_upgrade_bonus(target.target_date, timezone.now())

            SubmittedContribution.objects.create(
                user=self.user,
                contribution_type=contribution_type,
                proposed_points=points,
                contribution_date=timezone.now(),
                notes=f"Automatic submission for node upgrade to version {target.version} [{network}]",
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
