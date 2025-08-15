from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings
from django.utils import timezone
from utils.models import BaseModel
from datetime import timedelta
import re


class UserManager(BaseUserManager):
    """
    Custom manager for the User model.
    """
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password.
        """
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser, BaseModel):
    """
    Custom User model with email as the unique identifier.
    Includes additional fields for name and address.
    """
    # Make email the unique identifier
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, blank=True)

    # Additional fields
    name = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=42, blank=True, null=True,
                              help_text="Ethereum wallet address associated with this user")
    visible = models.BooleanField(default=True, help_text="Whether this user should be visible in API responses.")
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['address'],
                condition=models.Q(address__isnull=False),
                name='unique_address_when_not_null'
            )
        ]

    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email is already required by default

    objects = UserManager()

    def __str__(self):
        return self.email


class Validator(BaseModel):
    """
    Represents a validator with their node version information.
    One-to-one relationship with User.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='validator'
    )
    node_version = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Current node version (e.g., 1.2.3)"
    )
    
    def __str__(self):
        return f"{self.user.email} - Node: {self.node_version or 'Not set'}"
    
    def clean_version(self, version_str):
        """
        Extract semantic version numbers from a version string.
        Removes prefixes like 'v' and suffixes like '-rc1'.
        Returns tuple of (major, minor, patch) or None if invalid.
        """
        if not version_str:
            return None
            
        # Remove common prefixes and extract version numbers
        # First try to match X.Y.Z format
        match = re.match(r'v?(\d+)\.(\d+)\.(\d+)', version_str)
        if match:
            return tuple(map(int, match.groups()))
        
        # Then try X.Y format (assume patch version 0)
        match = re.match(r'v?(\d+)\.(\d+)', version_str)
        if match:
            major, minor = map(int, match.groups())
            return (major, minor, 0)
        
        # Finally try just X format (assume minor and patch 0)
        match = re.match(r'v?(\d+)', version_str)
        if match:
            major = int(match.group(1))
            return (major, 0, 0)
            
        return None
    
    def version_matches_or_higher(self, target_version):
        """
        Check if the validator's version matches or is higher than the target.
        Uses semantic versioning comparison.
        """
        if not self.node_version or not target_version:
            return False
            
        current = self.clean_version(self.node_version)
        target = self.clean_version(target_version)
        
        if not current or not target:
            # If can't parse as semver, fall back to exact string match
            return self.node_version == target_version
            
        # Compare semantic versions
        return current >= target
    
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
            from leaderboard.models import GlobalLeaderboardMultiplier
            
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
