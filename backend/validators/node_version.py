"""
Node version tracking and points calculation for validators.
"""
from django.db import models
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

    def full_clean(self, exclude=None, validate_unique=True, validate_constraints=True):
        self._node_version_validation_exclude = set(exclude or [])
        try:
            super().full_clean(
                exclude=exclude,
                validate_unique=validate_unique,
                validate_constraints=validate_constraints,
            )
        finally:
            if hasattr(self, '_node_version_validation_exclude'):
                delattr(self, '_node_version_validation_exclude')

    def clean(self):
        """Validate the node version format for both networks."""
        super().clean()

        pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9\-\.]+)?(\+[a-zA-Z0-9\-\.]+)?$'
        excluded_fields = getattr(self, '_node_version_validation_exclude', set())

        if 'node_version_asimov' not in excluded_fields and self.node_version_asimov:
            if not re.match(pattern, self.node_version_asimov):
                raise ValidationError({
                    'node_version_asimov': 'Node version must follow semantic versioning (e.g., 0.3.9, 1.2.3-beta.1)'
                })

        if 'node_version_bradbury' not in excluded_fields and self.node_version_bradbury:
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
