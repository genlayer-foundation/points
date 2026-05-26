from django.db.models import Count, F, IntegerField, Sum, Value
from django.db.models.functions import Greatest

from contributions.models import Contribution, ContributionDiscordXPState
from social_connections.models import DiscordConnection

from .constants import COMMUNITY_XP_EXCLUDED_TYPE_SLUGS
from .models import Mee6CurrentXP, Mee6SyncRun
from .services import get_default_guild_id


def get_latest_applied_sync(guild_id=None):
    guild_id = str(guild_id or get_default_guild_id())
    return (
        Mee6SyncRun.objects
        .filter(
            guild_id=guild_id,
            status=Mee6SyncRun.STATUS_SUCCESS,
            completed_at__isnull=False,
            applied_at__isnull=False,
        )
        .order_by('-applied_at', '-completed_at', '-id')
        .first()
    )


def _community_contributions(user_ids=None):
    queryset = Contribution.objects.filter(
        contribution_type__category__slug='community',
    ).exclude(
        contribution_type__slug__in=COMMUNITY_XP_EXCLUDED_TYPE_SLUGS,
    )
    if user_ids is not None:
        queryset = queryset.filter(user_id__in=user_ids)
    return queryset


def _aggregate_community_points(user_ids=None):
    return {
        row['user_id']: {
            'total': row['total'] or 0,
            'count': row['count'] or 0,
        }
        for row in _community_contributions(user_ids=user_ids)
            .values('user_id')
            .annotate(total=Sum('frozen_global_points'), count=Count('id'))
    }


def _discord_xp_states(user_ids=None):
    queryset = ContributionDiscordXPState.objects.filter(
        contribution__contribution_type__category__slug='community',
    ).exclude(
        contribution__contribution_type__slug__in=COMMUNITY_XP_EXCLUDED_TYPE_SLUGS,
    )
    if user_ids is not None:
        queryset = queryset.filter(contribution__user_id__in=user_ids)
    return queryset


def _aggregate_pending_portal_points(user_ids=None):
    pending_expr = Greatest(
        F('contribution__frozen_global_points') - F('awarded_amount'),
        Value(0),
        output_field=IntegerField(),
    )
    return {
        row['contribution__user_id']: row['pending_total'] or 0
        for row in _discord_xp_states(user_ids=user_ids)
            .values('contribution__user_id')
            .annotate(pending_total=Sum(pending_expr))
    }


def _aggregate_missing_state_portal_points(user_ids=None):
    return {
        row['user_id']: row['total'] or 0
        for row in _community_contributions(user_ids=user_ids)
            .filter(discord_xp_state__isnull=True)
            .values('user_id')
            .annotate(total=Sum('frozen_global_points'))
    }


def _current_xp_by_user(users_by_id, guild_id):
    if not users_by_id:
        return {}

    connections = (
        DiscordConnection.objects
        .filter(user_id__in=users_by_id.keys())
        .exclude(platform_user_id='')
        .select_related('user')
    )
    user_by_discord_id = {
        str(connection.platform_user_id): connection.user_id
        for connection in connections
    }
    if not user_by_discord_id:
        return {}

    current_rows = Mee6CurrentXP.objects.filter(
        guild_id=guild_id,
        discord_id__in=user_by_discord_id.keys(),
    )

    result = {}
    for current in current_rows:
        user_id = user_by_discord_id.get(str(current.discord_id))
        if not user_id:
            continue
        existing = result.get(user_id)
        if existing is None or current.xp > existing.xp:
            result[user_id] = current
    return result


def build_effective_community_scores(user_ids=None, guild_id=None, visible_only=True):
    from users.models import User

    guild_id = str(guild_id or get_default_guild_id())
    user_queryset = User.objects.all()
    if visible_only:
        user_queryset = user_queryset.filter(visible=True)
    if user_ids is not None:
        user_queryset = user_queryset.filter(id__in=user_ids)

    users_by_id = {
        user.id: user
        for user in user_queryset.only(
            'id',
            'name',
            'address',
            'profile_image_url',
            'visible',
        )
    }

    latest_sync = get_latest_applied_sync(guild_id)
    all_time = _aggregate_community_points(user_ids=users_by_id.keys())
    pending_portal_points_by_user = _aggregate_pending_portal_points(user_ids=users_by_id.keys())
    for user_id, missing_state_points in _aggregate_missing_state_portal_points(
        user_ids=users_by_id.keys()
    ).items():
        pending_portal_points_by_user[user_id] = (
            pending_portal_points_by_user.get(user_id, 0) + missing_state_points
        )
    current_xp_by_user = _current_xp_by_user(users_by_id, guild_id)

    candidate_user_ids = set(users_by_id.keys() if user_ids is not None else [])
    candidate_user_ids.update(all_time.keys())
    candidate_user_ids.update(pending_portal_points_by_user.keys())
    candidate_user_ids.update(current_xp_by_user.keys())

    scores = {}
    for user_id in candidate_user_ids:
        user = users_by_id.get(user_id)
        if not user:
            continue

        all_time_points = all_time.get(user_id, {}).get('total', 0)
        all_time_count = all_time.get(user_id, {}).get('count', 0)
        pending_portal_points = pending_portal_points_by_user.get(user_id, 0)
        current_xp = current_xp_by_user.get(user_id)
        discord_xp = current_xp.xp if current_xp else 0

        total_points = discord_xp + pending_portal_points

        scores[user_id] = {
            'user': user,
            'discord_xp': discord_xp,
            'discord_xp_synced_at': current_xp.synced_at if current_xp else None,
            'pending_portal_points': pending_portal_points,
            'tracked_portal_points_all_time': all_time_points,
            'total_points': total_points,
            'has_discord_xp_snapshot': current_xp is not None,
            'latest_sync_completed_at': latest_sync.completed_at if latest_sync else None,
            'latest_applied_sync_completed_at': latest_sync.completed_at if latest_sync else None,
            'latest_applied_at': latest_sync.applied_at if latest_sync else None,
            'community_contribution_count': all_time_count,
        }

    return scores


def get_effective_community_points(user, guild_id=None):
    scores = build_effective_community_scores(
        user_ids=[user.id],
        guild_id=guild_id,
        visible_only=False,
    )
    return scores.get(user.id, {
        'user': user,
        'discord_xp': 0,
        'discord_xp_synced_at': None,
        'pending_portal_points': 0,
        'tracked_portal_points_all_time': 0,
        'total_points': 0,
        'has_discord_xp_snapshot': False,
        'latest_sync_completed_at': None,
        'latest_applied_sync_completed_at': None,
        'latest_applied_at': None,
        'community_contribution_count': 0,
    })
