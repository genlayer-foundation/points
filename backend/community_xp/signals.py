from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from social_connections.models import DiscordConnection

from .services import clear_current_xp_match_for_connection, match_current_xp_for_connection


@receiver(pre_save, sender=DiscordConnection)
def clear_mee6_xp_before_discord_relink(sender, instance, **kwargs):
    if not instance.pk:
        instance._mee6_platform_user_id_changed = True
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._mee6_platform_user_id_changed = True
        return

    platform_user_id_changed = previous.platform_user_id != instance.platform_user_id
    instance._mee6_platform_user_id_changed = platform_user_id_changed

    if platform_user_id_changed:
        clear_current_xp_match_for_connection(previous)


@receiver(post_save, sender=DiscordConnection)
def match_mee6_xp_after_discord_link(sender, instance, created, **kwargs):
    if not created and not getattr(instance, '_mee6_platform_user_id_changed', False):
        return
    match_current_xp_for_connection(instance)


@receiver(post_delete, sender=DiscordConnection)
def clear_mee6_xp_after_discord_unlink(sender, instance, **kwargs):
    clear_current_xp_match_for_connection(instance)
