"""Automatic assignment of earned community Discord roles (Synapse/Brain).

Portal → Discord is add-only: a role is assigned when its threshold is met and
never removed by this system. Each role's threshold is evaluated independently.
"""

from django.conf import settings
from django.db import transaction
from django.db.models import Count

from tally.middleware.logging_utils import get_app_logger

from .discord_roles import (
    DiscordRoleSyncConfigurationError,
    DiscordRoleSyncService,
    DiscordRoleSyncUnavailable,
)
from .models import DiscordConnection, DiscordEarnedRoleAssignment

logger = get_app_logger('discord_roles')

SYNAPSE_CP = 14_000
SYNAPSE_POAPS = 8
BRAIN_CP = 80_000
BRAIN_POAPS = 16

# Discord failures that cannot self-heal within a run (rate limit, missing
# Manage Roles permission / role hierarchy): abort and let the next run retry.
ABORT_STATUS_CODES = (429, 401, 403)


def _configured_role_ids():
    role_ids = {
        'synapse': str(getattr(settings, 'DISCORD_SYNAPSE_ROLE_ID', '') or ''),
        'brain': str(getattr(settings, 'DISCORD_BRAIN_ROLE_ID', '') or ''),
        'neurocreative': str(getattr(settings, 'DISCORD_NEUROCREATIVE_ROLE_ID', '') or ''),
    }
    if not all(role_ids.values()):
        return None
    return role_ids


def _wanted_roles(role_ids, total_points, poap_count, held_role_ids):
    wanted = []
    if (
        total_points >= SYNAPSE_CP
        and poap_count >= SYNAPSE_POAPS
        and role_ids['synapse'] not in held_role_ids
    ):
        wanted.append(('synapse', role_ids['synapse']))
    if (
        total_points >= BRAIN_CP
        and poap_count >= BRAIN_POAPS
        and role_ids['neurocreative'] in held_role_ids
        and role_ids['brain'] not in held_role_ids
    ):
        wanted.append(('brain', role_ids['brain']))
    return wanted


def assign_earned_community_roles(dry_run=False, service=None):
    """Assign missing Synapse/Brain roles to every qualifying user.

    Returns stats plus the list of (would-be) assignments.
    """
    from community_xp.utils import build_effective_community_scores_queryset
    from poaps.models import PoapClaim

    stats = {
        'checked': 0,
        'synapse_assigned': 0,
        'brain_assigned': 0,
        'skipped_not_member': 0,
        'errors': 0,
        'aborted': False,
        'assignments': [],
    }

    role_ids = _configured_role_ids()
    if role_ids is None:
        logger.info("Earned role assignment skipped: Discord role IDs not configured")
        return stats

    candidates = (
        build_effective_community_scores_queryset(visible_only=True)
        .filter(total_points__gte=SYNAPSE_CP)
    )
    points_by_user_id = {user.id: user.total_points or 0 for user in candidates}
    if not points_by_user_id:
        return stats

    poaps_by_user_id = {
        row['user_id']: row['n']
        for row in (
            PoapClaim.objects
            .filter(user_id__in=points_by_user_id.keys())
            .values('user_id')
            .annotate(n=Count('id'))
        )
    }

    connections = (
        DiscordConnection.objects
        .filter(user_id__in=points_by_user_id.keys())
        .select_related('user')
        .prefetch_related('current_roles')
    )

    service = service or DiscordRoleSyncService()

    for connection in connections:
        stats['checked'] += 1
        if not connection.guild_member:
            stats['skipped_not_member'] += 1
            continue

        total_points = points_by_user_id.get(connection.user_id, 0)
        poap_count = poaps_by_user_id.get(connection.user_id, 0)
        held = {role.role_id for role in connection.current_roles.all()}

        for label, role_id in _wanted_roles(role_ids, total_points, poap_count, held):
            if not dry_run:
                try:
                    audit_reason = (
                        f'Automatic earned role assignment: {label} '
                        f'({total_points} CP, {poap_count} POAPs)'
                    )
                    assigned = service.add_member_role(
                        connection.platform_user_id,
                        role_id,
                        audit_log_reason=audit_reason,
                    )
                except DiscordRoleSyncConfigurationError as exc:
                    logger.warning("Earned role assignment aborted: %s", exc)
                    stats['errors'] += 1
                    stats['aborted'] = True
                    return stats
                except DiscordRoleSyncUnavailable as exc:
                    stats['errors'] += 1
                    if exc.status_code in ABORT_STATUS_CODES:
                        logger.warning("Earned role assignment aborted: %s", exc)
                        stats['aborted'] = True
                        return stats
                    logger.warning(
                        "Failed to assign %s role to connection %s: %s",
                        label,
                        connection.id,
                        exc,
                    )
                    continue

                if not assigned:
                    stats['skipped_not_member'] += 1
                    continue

                with transaction.atomic():
                    connection.current_roles.add(*service._get_or_create_missing_roles([role_id]))
                    DiscordEarnedRoleAssignment.objects.create(
                        connection=connection,
                        discord_user_id=connection.platform_user_id,
                        discord_username=connection.platform_username,
                        role_id=role_id,
                        role_name=label,
                        total_points=total_points,
                        poap_count=poap_count,
                    )
                logger.info(
                    "Assigned %s role to user %s (discord %s): %s CP, %s POAPs",
                    label,
                    connection.user_id,
                    connection.platform_user_id,
                    total_points,
                    poap_count,
                )

            stats[f'{label}_assigned'] += 1
            stats['assignments'].append({
                'user_id': connection.user_id,
                'user_name': connection.user.name or connection.user.email,
                'discord_username': connection.platform_username,
                'role': label,
                'total_points': total_points,
                'poap_count': poap_count,
            })

    return stats
