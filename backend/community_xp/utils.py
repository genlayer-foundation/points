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


def _community_social_task_completions(user_ids=None):
    from social_tasks.models import SocialTaskCompletion

    queryset = SocialTaskCompletion.objects.filter(
        task__category__slug='community',
    )
    if user_ids is not None:
        queryset = queryset.filter(user_id__in=user_ids)
    return queryset


def _discord_xp_states(user_ids=None):
    queryset = ContributionDiscordXPState.objects.filter(
        contribution__contribution_type__category__slug='community',
    ).exclude(
        contribution__contribution_type__slug__in=COMMUNITY_XP_EXCLUDED_TYPE_SLUGS,
    )
    if user_ids is not None:
        queryset = queryset.filter(contribution__user_id__in=user_ids)
    return queryset


def _pending_points_case(points_field, state_field, baseline_completed_at=None):
    points = F(points_field)
    if baseline_completed_at is None:
        return points

    pending_expr = Greatest(
        points - F(f'{state_field}__awarded_amount'),
        Value(0),
        output_field=IntegerField(),
    )
    return Case(
        When(**{f'{state_field}__isnull': True}, then=points),
        When(
            **{
                f'{state_field}__status': ContributionDiscordXPState.STATUS_DISTRIBUTED,
                f'{state_field}__distributed_at__lte': baseline_completed_at,
            },
            then=Value(0),
        ),
        When(
            **{
                f'{state_field}__status': ContributionDiscordXPState.STATUS_DISTRIBUTED,
                f'{state_field}__distributed_at__gt': baseline_completed_at,
            },
            then=points,
        ),
        default=pending_expr,
        output_field=IntegerField(),
    )


def _build_effective_community_scores_queryset(
    user_ids=None,
    guild_id=None,
    visible_only=True,
    include_details=True,
):
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
    community_social_tasks = (
        _community_social_task_completions()
        .filter(user_id=OuterRef('pk'))
        .values('user_id')
    )
    pending_points_queryset = (
        community_contributions
        .annotate(pending_total=Sum(_pending_points_case(
            'frozen_global_points',
            'discord_xp_state',
            latest_sync.completed_at if latest_sync else None,
        )))
        .values('pending_total')[:1]
    )
    pending_social_task_points_queryset = (
        community_social_tasks
        .annotate(pending_total=Sum(_pending_points_case(
            'points_awarded',
            'discord_xp_state',
            latest_sync.completed_at if latest_sync else None,
        )))
        .values('pending_total')[:1]
    )
    annotations = {
        'discord_xp': Coalesce(
            Subquery(current_xp_queryset.values('xp')[:1], output_field=IntegerField()),
            Value(0),
            output_field=IntegerField(),
        ),
        'pending_portal_points': Coalesce(
            Subquery(pending_points_queryset, output_field=IntegerField()),
            Value(0),
            output_field=IntegerField(),
        ),
        'pending_social_task_points': Coalesce(
            Subquery(pending_social_task_points_queryset, output_field=IntegerField()),
            Value(0),
            output_field=IntegerField(),
        ),
    }
    selected_fields = ('id', 'name')

    if include_details:
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
        all_time_social_task_points_queryset = (
            community_social_tasks
            .annotate(total=Sum('points_awarded'))
            .values('total')[:1]
        )
        social_task_count_queryset = (
            community_social_tasks
            .annotate(count=Count('id'))
            .values('count')[:1]
        )
        annotations.update({
            'discord_xp_synced_at': Subquery(
                current_xp_queryset.values('synced_at')[:1],
                output_field=DateTimeField(),
            ),
            'current_xp_row_id': Subquery(
                current_xp_queryset.values('id')[:1],
                output_field=IntegerField(),
            ),
            'tracked_portal_points_all_time': Coalesce(
                Subquery(all_time_points_queryset, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            ),
            'community_contribution_count': Coalesce(
                Subquery(contribution_count_queryset, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            ),
            'tracked_social_task_points_all_time': Coalesce(
                Subquery(all_time_social_task_points_queryset, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            ),
            'community_social_task_count': Coalesce(
                Subquery(social_task_count_queryset, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            ),
            'latest_applied_sync_completed_at': Value(
                latest_sync.completed_at if latest_sync else None,
                output_field=DateTimeField(),
            ),
            'latest_applied_at': Value(
                latest_sync.applied_at if latest_sync else None,
                output_field=DateTimeField(),
            ),
        })
        selected_fields = ('id', 'name', 'address', 'profile_image_url', 'visible')

    queryset = (
        user_queryset
        .only(*selected_fields)
        .annotate(**annotations)
        .annotate(
            total_points=(
                F('discord_xp')
                + F('pending_portal_points')
                + F('pending_social_task_points')
            ),
            community_sort_name=Lower(Coalesce('name', Value(''))),
        )
    )

    if include_details:
        queryset = queryset.annotate(
            has_discord_xp_snapshot=Case(
                When(current_xp_row_id__isnull=False, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )

    return queryset


def build_effective_community_scores_queryset(user_ids=None, guild_id=None, visible_only=True):
    """
    Return users annotated with the full effective community score breakdown.

    Effective points are MEE6 current XP plus contribution and social-task
    points not covered by the applied MEE6 baseline.
    """
    return _build_effective_community_scores_queryset(
        user_ids=user_ids,
        guild_id=guild_id,
        visible_only=visible_only,
        include_details=True,
    )


def build_effective_community_ranking_queryset(
    user_ids=None,
    guild_id=None,
    visible_only=True,
):
    """Return users annotated only with fields needed to rank community scores."""
    return _build_effective_community_scores_queryset(
        user_ids=user_ids,
        guild_id=guild_id,
        visible_only=visible_only,
        include_details=False,
    )


def effective_community_ranking_queryset(user_ids=None, guild_id=None, visible_only=True):
    return (
        build_effective_community_ranking_queryset(
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
            'pending_social_task_points': user.pending_social_task_points,
            'tracked_portal_points_all_time': user.tracked_portal_points_all_time,
            'tracked_social_task_points_all_time': user.tracked_social_task_points_all_time,
            'total_points': user.total_points,
            'has_discord_xp_snapshot': user.has_discord_xp_snapshot,
            'latest_applied_sync_completed_at': user.latest_applied_sync_completed_at,
            'latest_applied_at': user.latest_applied_at,
            'community_contribution_count': user.community_contribution_count,
            'community_social_task_count': user.community_social_task_count,
        }

    return scores


def get_community_member_user_ids(user_ids=None, guild_id=None, visible_only=True, since=None):
    from creators.models import Creator
    from poaps.models import PoapClaim

    guild_id = str(guild_id or get_default_guild_id())
    latest_sync = get_latest_applied_sync(guild_id)

    positive_xp = Mee6CurrentXP.objects.filter(
        guild_id=guild_id,
        matched_user__isnull=False,
        xp__gt=0,
    )
    pending_social_tasks = (
        _community_social_task_completions(user_ids=user_ids)
        .annotate(pending_points=_pending_points_case(
            'points_awarded',
            'discord_xp_state',
            latest_sync.completed_at if latest_sync else None,
        ))
        .filter(pending_points__gt=0)
    )
    if visible_only:
        positive_xp = positive_xp.filter(matched_user__visible=True)
        pending_social_tasks = pending_social_tasks.filter(user__visible=True)
    if user_ids is not None:
        positive_xp = positive_xp.filter(matched_user_id__in=user_ids)

    eligible_member_user_ids = set(
        positive_xp.values_list('matched_user_id', flat=True).distinct()
    )
    eligible_member_user_ids.update(
        pending_social_tasks.values_list('user_id', flat=True).distinct()
    )

    member_contributions = _community_member_contributions(user_ids=user_ids)
    if visible_only:
        member_contributions = member_contributions.filter(user__visible=True)
    eligible_member_user_ids.update(
        member_contributions
        .values_list('user_id', flat=True)
        .distinct()
    )
    member_user_ids = set(eligible_member_user_ids if since is None else [])

    poap_filters = {
        'user__isnull': False,
    }
    if visible_only:
        poap_filters['user__visible'] = True
    if user_ids is not None:
        poap_filters['user_id__in'] = user_ids
    if since is not None:
        poap_filters['created_at__gte'] = since
        member_user_ids.update(
            member_contributions
            .filter(created_at__gte=since)
            .values_list('user_id', flat=True)
            .distinct()
        )
        recent_social_tasks = _community_social_task_completions(user_ids=user_ids)
        if visible_only:
            recent_social_tasks = recent_social_tasks.filter(user__visible=True)
        member_user_ids.update(
            recent_social_tasks
            .filter(completed_at__gte=since)
            .values_list('user_id', flat=True)
            .distinct()
        )
        creator_filters = {
            'user_id__in': eligible_member_user_ids,
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
        'pending_social_task_points': 0,
        'tracked_portal_points_all_time': 0,
        'tracked_social_task_points_all_time': 0,
        'total_points': 0,
        'has_discord_xp_snapshot': False,
        'latest_applied_sync_completed_at': None,
        'latest_applied_at': None,
        'community_contribution_count': 0,
        'community_social_task_count': 0,
    })
