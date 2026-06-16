"""Signal receivers that turn domain events into notifications.

Producers that are simple model creations hook here so the notification
trigger lives in one app; flows with more context (submission reviews,
referrals, admin broadcasts) call notifications.services directly.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from contributions.models import ContributionHighlight

from . import services


@receiver(post_save, sender=ContributionHighlight, dispatch_uid='notifications_contribution_highlighted')
def on_contribution_highlighted(sender, instance, created, **kwargs):
    if created:
        services.notify_contribution_highlighted(instance)
