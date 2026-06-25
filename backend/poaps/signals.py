from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .services import attach_unmatched_claims_for_user


@receiver(post_save, sender=get_user_model())
def attach_legacy_poap_claims(sender, instance, **kwargs):
    attach_unmatched_claims_for_user(instance)
