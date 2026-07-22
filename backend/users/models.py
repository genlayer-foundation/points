import secrets
import string

from django.db import IntegrityError, models, transaction
from django.contrib.auth.models import AbstractUser, BaseUserManager
from utils.models import BaseModel


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
    can_view_role_sections = models.BooleanField(
        default=False,
        help_text=(
            "Allow read-only access to gated Builder, Validator, and Community "
            "portal sections. This does not grant a role, interaction permissions, "
            "or access to Steward tools."
        ),
    )
    
    # Profile fields
    description = models.TextField(max_length=500, blank=True, 
                                 help_text="User bio/description")
    banner_image_url = models.URLField(max_length=500, blank=True,
                                      help_text="Cloudinary URL for banner image (1500x500)")
    profile_image_url = models.URLField(max_length=500, blank=True,
                                       help_text="Cloudinary URL for profile image (400x400)")
    website = models.URLField(blank=True, help_text="User's website URL")

    twitter_handle = models.CharField(max_length=50, blank=True,
                                     help_text="Twitter/X username without @")
    discord_handle = models.CharField(max_length=50, blank=True,
                                     help_text="Discord username")
    telegram_handle = models.CharField(max_length=50, blank=True,
                                      help_text="Telegram username without @")
    linkedin_handle = models.CharField(max_length=100, blank=True,
                                      help_text="LinkedIn username or profile URL slug")

    # GitHub OAuth fields
    github_username = models.CharField(max_length=100, blank=True,
                                      help_text="GitHub username from OAuth")
    github_user_id = models.CharField(max_length=50, blank=True,
                                     help_text="GitHub user ID for unique identification")
    github_access_token = models.TextField(blank=True,
                                          help_text="Encrypted GitHub access token")
    github_linked_at = models.DateTimeField(null=True, blank=True,
                                           help_text="When GitHub account was linked")

    # Email verification
    is_email_verified = models.BooleanField(default=False,
                                           help_text="Whether the email is user-provided (True) or auto-generated (False)")
    email_verified_at = models.DateTimeField(null=True, blank=True,
                                             help_text="When the current email address was verified")
    
    # Cloudinary metadata (for deletion/management)
    profile_image_public_id = models.CharField(max_length=255, blank=True,
                                              help_text="Cloudinary public ID for profile image")
    banner_image_public_id = models.CharField(max_length=255, blank=True,
                                            help_text="Cloudinary public ID for banner image")
    
    # Referral system
    referral_code = models.CharField(max_length=8, unique=True, null=True, blank=True,
                                   help_text="Unique 8-character alphanumeric referral code")
    referred_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='referrals',
                                   help_text="User who referred this user")

    # Ban system
    is_banned = models.BooleanField(default=False,
                                    help_text="Whether this user is banned from submitting")
    ban_reason = models.TextField(blank=True, default='',
                                  help_text="Reason for the ban (shown to user)")
    banned_at = models.DateTimeField(null=True, blank=True,
                                     help_text="When the user was banned")
    banned_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='users_banned',
                                  help_text="User/steward who banned this user")

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

    def ensure_referral_code(self):
        """
        Return this user's referral code, creating one if an old account is
        missing the backfilled value.
        """
        if self.referral_code:
            return self.referral_code

        user_model = type(self)
        characters = string.ascii_uppercase + string.digits
        for _ in range(100):
            code = ''.join(secrets.choice(characters) for _ in range(8))
            if user_model.objects.filter(referral_code=code).exists():
                continue

            try:
                with transaction.atomic():
                    updated = user_model.objects.filter(
                        pk=self.pk,
                        referral_code__isnull=True,
                    ).update(referral_code=code)
                    if not updated:
                        updated = user_model.objects.filter(
                            pk=self.pk,
                            referral_code='',
                        ).update(referral_code=code)
            except IntegrityError:
                continue

            if updated:
                self.referral_code = code
                return code

            existing_code = user_model.objects.only('referral_code').get(pk=self.pk).referral_code
            if existing_code:
                self.referral_code = existing_code
                return existing_code

        raise ValueError("Unable to generate unique referral code after maximum attempts")

    def __str__(self):
        return self.email


class BanAppeal(BaseModel):
    """
    One-time appeal from a banned user requesting their ban be lifted.
    Each user can only submit one appeal.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ban_appeals')
    appeal_text = models.TextField(help_text="User's explanation for why the ban should be lifted")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='reviewed_appeals',
                                    help_text="Steward who reviewed this appeal")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, default='',
                                    help_text="Internal notes from the reviewer")

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user'], name='unique_ban_appeal_per_user'),
        ]

    def __str__(self):
        return f"Appeal by {self.user.email} ({self.status})"
