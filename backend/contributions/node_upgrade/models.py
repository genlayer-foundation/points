from django.db import models
from django.core.exceptions import ValidationError
from utils.models import BaseModel


class TargetNodeVersion(BaseModel):
    """
    Represents the target node version that validators should upgrade to.
    Only one can be active at a time per network.
    """
    NETWORK_CHOICES = [
        ('asimov', 'Asimov'),
        ('bradbury', 'Bradbury'),
    ]

    version = models.CharField(
        max_length=100,
        help_text="Target node version (e.g., 1.2.3)"
    )
    network = models.CharField(
        max_length=20,
        choices=NETWORK_CHOICES,
        default='asimov',
        help_text="Which network this target version applies to"
    )
    target_date = models.DateTimeField(
        help_text="Date when this version becomes available for upgrade (used for early upgrade bonus calculation)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only one target can be active at a time per network"
    )

    class Meta:
        verbose_name = "Target Node Version"
        verbose_name_plural = "Target Node Versions"
        ordering = ['-created_at']

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"Target: {self.version} [{self.network}] (available from {self.target_date.strftime('%Y-%m-%d')}) - {status}"

    def save(self, *args, **kwargs):
        """
        Ensure only one target is active at a time per network.
        """
        if self.is_active:
            # Deactivate all other targets for the same network
            TargetNodeVersion.objects.filter(
                is_active=True, network=self.network
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def clean(self):
        """
        Validate the target version data.
        """
        super().clean()

        # If trying to deactivate, ensure there's at least one active for this network
        if not self.is_active and self.pk:
            active_count = TargetNodeVersion.objects.filter(
                is_active=True, network=self.network
            ).exclude(pk=self.pk).count()
            if active_count == 0:
                raise ValidationError(
                    f"There must be at least one active target version for the {self.network} network."
                )

    @classmethod
    def get_active(cls, network=None):
        """
        Get the currently active target version.
        If network is specified, returns the active target for that network.
        If network is None, returns the first active target (backward compat).
        Returns None if no active target exists.
        """
        qs = cls.objects.filter(is_active=True)
        if network:
            qs = qs.filter(network=network)
        return qs.first()