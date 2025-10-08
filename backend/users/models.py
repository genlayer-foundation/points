from django.db import models
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
    
    # Profile fields
    description = models.TextField(max_length=500, blank=True, 
                                 help_text="User bio/description")
    banner_image_url = models.URLField(max_length=500, blank=True,
                                      help_text="Cloudinary URL for banner image (1500x500)")
    profile_image_url = models.URLField(max_length=500, blank=True,
                                       help_text="Cloudinary URL for profile image (400x400)")
    website = models.URLField(blank=True, help_text="User's website URL")
    
    # Contact information
    contact_email = models.EmailField(blank=True, 
                                     help_text="Public contact email (different from auth email)")
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
