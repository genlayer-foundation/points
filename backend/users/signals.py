import string
import secrets
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User


def generate_unique_referral_code():
    """
    Generate a unique 8-character alphanumeric referral code.
    Retries until a unique code is found.
    """
    characters = string.ascii_uppercase + string.digits  # A-Z, 0-9
    max_attempts = 100
    
    for _ in range(max_attempts):
        code = ''.join(secrets.choice(characters) for _ in range(8))
        if not User.objects.filter(referral_code=code).exists():
            return code
    
    # If we can't find a unique code after max_attempts, raise an error
    raise ValueError("Unable to generate unique referral code after maximum attempts")


@receiver(post_save, sender=User)
def create_referral_code(sender, instance, created, **kwargs):
    """
    Automatically generate a unique referral code for new users.
    """
    if created and not instance.referral_code:
        try:
            referral_code = generate_unique_referral_code()
            # Use update to avoid triggering the signal again
            User.objects.filter(pk=instance.pk).update(referral_code=referral_code)
        except ValueError as e:
            # Log the error but don't fail user creation
            print(f"Warning: Failed to generate referral code for user {instance.id}: {str(e)}")