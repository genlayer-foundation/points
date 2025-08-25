from django.db import models
from django.core.exceptions import ValidationError
from utils.models import BaseModel


class TargetNodeVersion(BaseModel):
    """
    Represents the target node version that validators should upgrade to.
    Only one can be active at a time.
    """
    version = models.CharField(
        max_length=100,
        help_text="Target node version (e.g., 1.2.3)"
    )
    target_date = models.DateTimeField(
        help_text="Date when this version becomes available for upgrade (used for early upgrade bonus calculation)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only one target can be active at a time"
    )
    
    class Meta:
        verbose_name = "Target Node Version"
        verbose_name_plural = "Target Node Versions"
        ordering = ['-created_at']
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"Target: {self.version} (available from {self.target_date.strftime('%Y-%m-%d')}) - {status}"
    
    def save(self, *args, **kwargs):
        """
        Ensure only one target is active at a time.
        """
        if self.is_active:
            # Deactivate all other targets
            TargetNodeVersion.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
    
    def clean(self):
        """
        Validate the target version data.
        """
        super().clean()
        
        # If trying to deactivate, ensure there's at least one active
        if not self.is_active and self.pk:
            active_count = TargetNodeVersion.objects.filter(is_active=True).exclude(pk=self.pk).count()
            if active_count == 0:
                raise ValidationError("There must be at least one active target version.")
    
    @classmethod
    def get_active(cls):
        """
        Get the currently active target version.
        Returns None if no active target exists.
        """
        return cls.objects.filter(is_active=True).first()