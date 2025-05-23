from django.db import models
from django.utils import timezone


class Nonce(models.Model):
    """
    Model to store nonce values for SIWE authentication.
    """
    value = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.value} - {'Used' if self.used else 'Unused'}"
        
    def is_valid(self):
        """Check if nonce is valid (not used and not expired)"""
        return not self.used and self.expires_at > timezone.now()
    
    def mark_as_used(self):
        """Mark the nonce as used"""
        self.used = True
        self.save()