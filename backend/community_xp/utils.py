from django.db.models import (
    BooleanField,
    Case,
    Count,
    DateTimeField,
    F,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Greatest, Lower

from contributions.models import Contribution, ContributionDiscordXPState

from .constants import COMMUNITY_MEMBER_EXCLUDED_TYPE_SLUGS, COMMUNITY_XP_EXCLUDED_TYPE_SLUGS
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


def _community_member_contributions(user_ids=None):
    queryset = Contribution.objects.filter(
        contribution_type__category__slug='community',
    ).exclude(
        contribution_type__slug__in=COMMUNITY_MEMBER_EXCLUDED_TYPE_SLUGS,
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


def _community_points_case(baseline_completed_at=None):
    if baseline_completed_at is None:
        return F('frozen_global_points')

    pending_expr = Greatest(
        F('frozen_global_points') - F('discord_xp_state__awarded_amount'),
        Value(0),
        output_field=IntegerField(),
    )
    return Case(
        When(discord_xp_state__isnull=True, then=F('frozen_global_points')),
        When(
            discord_xp_state__status=ContributionDiscordXPState.STATUS_DISTRIBUTED,
            discord_xp_state__distributed_at__lte=baseline_completed_at,
            then=Value(0),
        ),
        When(
            discord_xp_state__status=ContributionDiscordXPState.STATUS_DISTRIBUTED,
            discord_xp_state__distributed_at__gt=baseline_completed_at,
            then=F('frozen_global_points'),
        ),
        default=pending_expr,
        output_field=IntegerField(),
    )


def build_effective_community_scores_queryset(user_ids=None, guild_id=None, visible_only=True):
    """
    Return users annotated with the same effective community score fields as
    build_effective_community_scores(), without materializing the full ranking.
    Effective points are MEE6 current XP plus portal points not covered by the
    applied MEE6 baseline.
    """
    from users.models import User

    guild_id = str(guild_id or get_default_guild_id())
    user_queryset = User.objects.all()
    if visible_only:
        user_queryset = user_queryset.filter(visible=True)
    if user_ids is not None:
        user_queryset = user_queryset.filter(id__in=user_ids)

    latest_sync = get_latest_applied_sync(guild_id)

    current_xp_queryset = (
        Mee6CurrentXP.objects
        .filter(guild_id=guild_id, matched_user_id=OuterRef('pk'))
        .order_by('-xp', 'id')
    )
    community_contributions = (
        Contribution.objects
        .filter(
            user_id=OuterRef('pk'),
            contribution_type__category__slug='community',
        )
        .exclude(contribution_type__slug__in=COMMUNITY_XP_EXCLUDED_TYPE_SLUGS)
        .values('user_id')
    )
    pending_points_queryset = (
        community_contributions
        .annotate(pending_total=Sum(_community_points_case(
            latest_sync.completed_at if latest_sync else None
        )))
        .values('pending_total')[:1]
    )
    all_time_points_queryset = (
        community_contributions
        .annotate(total=Sum('frozen_global_points'))
        .values('total')[:1]
    )
    contribution_count_queryset = (
        community_contributions
        .annotate(count=Count('id'))
        .values('count')[:1]
    )

    return (
        user_queryset
        .only('id', 'name', 'address', 'profile_image_url', 'visible')
        .annotate(
            discord_xp=Coalesce(
                Subquery(current_xp_queryset.values('xp')[:1], output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            ),
            discord_xp_synced_at=Subquery(
                current_xp_queryset.values('synced_at')[:1],
                output_field=DateTimeField(),
            ),
            current_xp_row_id=Subquery(
                current_xp_queryset.values('id')[:1],
                output_field=IntegerField(),
            ),
            pending_portal_points=Coalesce(
                Subquery(pending_points_queryset, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            ),
            tracked_portal_points_all_time=Coalesce(
                Subquery(all_time_points_queryset, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            ),
            community_contribution_count=Coalesce(
                Subquery(contribution_count_queryset, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            ),
            latest_applied_sync_completed_at=Value(
                latest_sync.completed_at if latest_sync else None,
                output_field=DateTimeField(),
            ),
            latest_applied_at=Value(
                latest_sync.applied_at if latest_sync else None,
                output_field=DateTimeField(),
            ),
        )
        .annotate(
            total_points=F('discord_xp') + F('pending_portal_points'),
            has_discord_xp_snapshot=Case(
                When(current_xp_row_id__isnull=False, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
            community_sort_name=Lower(Coalesce('name', Value(''))),
        )
    )


def effective_community_ranking_queryset(user_ids=None, guild_id=None, visible_only=True):
    return (
        build_effective_community_scores_queryset(
            user_ids=user_ids,
            guild_id=guild_id,
            visible_only=visible_only,
        )
        .filter(total_points__gt=0)
        .order_by('-total_points', 'community_sort_name', 'id')
    )


def build_effective_community_scores(user_ids=None, guild_id=None, visible_only=True):
    scores_queryset = build_effective_community_scores_queryset(
        user_ids=user_ids,
        guild_id=guild_id,
        visible_only=visible_only,
    )
    if user_ids is None:
        scores_queryset = scores_queryset.filter(
            Q(total_points__gt=0) | Q(community_contribution_count__gt=0)
        )

    scores = {}
    for user in scores_queryset:
        scores[user.id] = {
            'user': user,
            'discord_xp': user.discord_xp,
            'discord_xp_synced_at': user.discord_xp_synced_at,
            'pending_portal_points': user.pending_portal_points,
            'tracked_portal_points_all_time': user.tracked_portal_points_all_time,
            'total_points': user.total_points,
            'has_discord_xp_snapshot': user.has_discord_xp_snapshot,
            'latest_applied_sync_completed_at': user.latest_applied_sync_completed_at,
            'latest_applied_at': user.latest_applied_at,
            'community_contribution_count': user.community_contribution_count,
        }

    return scores


def get_community_member_user_ids(user_ids=None, guild_id=None, visible_only=True, since=None):
    from creators.models import Creator
    from poaps.models import PoapClaim

    score_queryset = effective_community_ranking_queryset(
        user_ids=user_ids,
        guild_id=guild_id,
        visible_only=visible_only,
    )
    score_member_user_ids = set(
        score_queryset
        .filter(discord_xp__gt=0)
        .values_list('id', flat=True)
    )
    member_contributions = _community_member_contributions(user_ids=user_ids)
    if visible_only:
        member_contributions = member_contributions.filter(user__visible=True)
    score_member_user_ids.update(
        member_contributions
        .values_list('user_id', flat=True)
        .distinct()
    )
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
