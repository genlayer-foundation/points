import string
import secrets
from django.db.models.signals import post_save
from django.dispatch import receiver

from tally.middleware.logging_utils import get_app_logger
from .models import User

logger = get_app_logger('users')


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
    if created or not instance.referral_code:
        try:
            referral_code = generate_unique_referral_code()
            # Use update to avoid triggering the signal again
            User.objects.filter(pk=instance.pk).update(referral_code=referral_code)
        except Exception as e:
            # Log the error but don't fail user creation
            logger.error(f"Failed to generate referral code: {str(e)}")