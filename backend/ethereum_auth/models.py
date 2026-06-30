from django.db import models
from django.conf import settings
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


class PendingWalletSignup(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONSUMED = 'consumed'
    STATUS_EXPIRED = 'expired'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONSUMED, 'Consumed'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    address = models.CharField(max_length=42, unique=True, db_index=True)
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    referral_code = models.CharField(max_length=8, blank=True)
    profile_data = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    last_email_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def is_active(self):
        return self.status == self.STATUS_PENDING and self.expires_at > timezone.now()

    def mark_consumed(self):
        self.status = self.STATUS_CONSUMED
        self.save(update_fields=['status', 'updated_at'])


class EmailVerificationToken(models.Model):
    PURPOSE_PENDING_SIGNUP = 'pending_signup'
    PURPOSE_EXISTING_USER = 'existing_user'
    PURPOSE_CHOICES = [
        (PURPOSE_PENDING_SIGNUP, 'Pending wallet signup'),
        (PURPOSE_EXISTING_USER, 'Existing user email verification'),
    ]

    purpose = models.CharField(max_length=32, choices=PURPOSE_CHOICES, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='email_verification_tokens',
    )
    pending_signup = models.ForeignKey(
        PendingWalletSignup,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='email_verification_tokens',
    )
    encrypted_email = models.TextField()
    email_fingerprint = models.CharField(max_length=64, db_index=True)
    token_lookup_hash = models.CharField(max_length=64, db_index=True)
    token_hash = models.CharField(max_length=128)
    attempts = models.PositiveSmallIntegerField(default=0)
    send_count = models.PositiveSmallIntegerField(default=1)
    last_sent_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['purpose', 'email_fingerprint', 'consumed_at']),
            models.Index(fields=['purpose', 'token_lookup_hash', 'consumed_at']),
        ]

    def is_active(self):
        return self.consumed_at is None and self.expires_at > timezone.now()
