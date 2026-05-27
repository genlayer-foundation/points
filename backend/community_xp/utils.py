from django.db.models import Case, Count, F, IntegerField, Sum, Value, When
from django.db.models.functions import Greatest

from contributions.models import Contribution, ContributionDiscordXPState

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


def _aggregate_pending_portal_points(user_ids=None, baseline_completed_at=None):
    pending_expr = Greatest(
        F('contribution__frozen_global_points') - F('awarded_amount'),
        Value(0),
        output_field=IntegerField(),
    )
    if baseline_completed_at is None:
        effective_pending_expr = F('contribution__frozen_global_points')
    else:
        effective_pending_expr = Case(
            When(
                status=ContributionDiscordXPState.STATUS_DISTRIBUTED,
                distributed_at__lte=baseline_completed_at,
                then=Value(0),
            ),
            When(
                status=ContributionDiscordXPState.STATUS_DISTRIBUTED,
                distributed_at__gt=baseline_completed_at,
                then=F('contribution__frozen_global_points'),
            ),
            default=pending_expr,
            output_field=IntegerField(),
        )

    return {
        row['contribution__user_id']: row['pending_total'] or 0
        for row in _discord_xp_states(user_ids=user_ids)
            .values('contribution__user_id')
            .annotate(pending_total=Sum(effective_pending_expr))
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

    current_rows = Mee6CurrentXP.objects.filter(
        guild_id=guild_id,
        matched_user_id__in=users_by_id.keys(),
    )

    result = {}
    for current in current_rows:
        user_id = current.matched_user_id
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

    all_time = _aggregate_community_points(user_ids=users_by_id.keys())
    latest_sync = get_latest_applied_sync(guild_id)
    pending_portal_points_by_user = _aggregate_pending_portal_points(
        user_ids=users_by_id.keys(),
        baseline_completed_at=latest_sync.completed_at if latest_sync else None,
    )
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
            'latest_applied_sync_completed_at': latest_sync.completed_at if latest_sync else None,
            'latest_applied_at': latest_sync.applied_at if latest_sync else None,
            'community_contribution_count': all_time_count,
        }

    return scores


def get_community_member_user_ids(user_ids=None, guild_id=None, visible_only=True, since=None):
    from creators.models import Creator
    from poaps.models import PoapClaim

    score_map = build_effective_community_scores(
        user_ids=user_ids,
        guild_id=guild_id,
        visible_only=visible_only,
    )
    score_member_user_ids = {
        user_id
        for user_id, score in score_map.items()
        if (score['total_points'] or 0) > 0
    }
    member_user_ids = set(score_member_user_ids if since is None else [])

    contribution_filters = {
        'contribution_type__category__slug': 'community',
        'contribution_type__is_submittable': True,
    }
    poap_filters = {
        'user__isnull': False,
    }
    if visible_only:
        contribution_filters['user__visible'] = True
        poap_filters['user__visible'] = True
    if user_ids is not None:
        contribution_filters['user_id__in'] = user_ids
        poap_filters['user_id__in'] = user_ids
    if since is not None:
        contribution_filters['created_at__gte'] = since
        poap_filters['created_at__gte'] = since
        recent_effective_contributions = _community_contributions(user_ids=user_ids)
        if visible_only:
            recent_effective_contributions = recent_effective_contributions.filter(user__visible=True)
        member_user_ids.update(
            recent_effective_contributions
            .filter(created_at__gte=since)
            .values_list('user_id', flat=True)
            .distinct()
        )
        creator_filters = {
            'user_id__in': score_member_user_ids,
            'created_at__gte': since,
        }
        if visible_only:
            creator_filters['user__visible'] = True
        member_user_ids.update(
            Creator.objects
            .filter(**creator_filters)
            .values_list('user_id', flat=True)
            .distinct()
        )

    member_user_ids.update(
        Contribution.objects
        .filter(**contribution_filters)
        .values_list('user_id', flat=True)
        .distinct()
    )
    member_user_ids.update(
        PoapClaim.objects
        .filter(**poap_filters)
        .values_list('user_id', flat=True)
        .distinct()
    )

    return member_user_ids


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
        'latest_applied_sync_completed_at': None,
        'latest_applied_at': None,
        'community_contribution_count': 0,
    })
