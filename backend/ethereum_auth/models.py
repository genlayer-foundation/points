from django.db import models
from django.utils import timezone


class Nonce(models.Model):
    """
    Model to store nonce values for SIWE authentication.
    """
    PURPOSE_LOGIN = 'login'
    PURPOSE_POAP_RECOVERY = 'poap_recovery'
    PURPOSE_CHOICES = [
        (PURPOSE_LOGIN, 'Login'),
        (PURPOSE_POAP_RECOVERY, 'POAP Recovery'),
    ]

    value = models.CharField(max_length=64, unique=True)
    purpose = models.CharField(
        max_length=32,
        choices=PURPOSE_CHOICES,
        default=PURPOSE_LOGIN,
        db_index=True,
    )
    created_at = models.DateTimeField(default=timezone.now)
    used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.value} ({self.purpose}) - {'Used' if self.used else 'Unused'}"
        
    def is_valid(self):
        """Check if nonce is valid (not used and not expired)"""
        return not self.used and self.expires_at > timezone.now()
    
    def mark_as_used(self):
        """Mark the nonce as used"""
        self.used = True
        self.save(update_fields=['used'])
