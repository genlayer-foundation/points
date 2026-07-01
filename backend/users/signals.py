from django.db.models.signals import post_save
from django.dispatch import receiver

from tally.middleware.logging_utils import get_app_logger
from .models import User

logger = get_app_logger('users')


@receiver(post_save, sender=User)
def create_referral_code(sender, instance, created, **kwargs):
    """
    Automatically generate a unique referral code for new users.
    """
    if created or not instance.referral_code:
        try:
            instance.ensure_referral_code()
        except Exception as e:
            # Log the error but don't fail user creation
            logger.error(f"Failed to generate referral code: {str(e)}")
