from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from tally.middleware.logging_utils import get_app_logger

from .models import Contribution, ContributionType

logger = get_app_logger('contributions')

REVIEWER_REWARD_TYPE_SLUG = 'project-review-reward'


def _score_value(section):
    if not isinstance(section, dict):
        return None
    try:
        return int(section.get('score'))
    except (TypeError, ValueError):
        return None


def compute_reviewer_reward(
    *,
    proposed_action,
    proposed_sections,
    final_action,
    final_sections,
    proposed_points=None,
    final_points=None,
):
    """Compute escrowed reviewer points from action, rubric, and point deltas."""
    if final_action != proposed_action or final_action not in ('accept', 'reject'):
        return 0

    proposed_sections = proposed_sections or {}
    final_sections = final_sections or {}
    delta = 0
    for key in proposed_sections.keys() & final_sections.keys():
        proposed_score = _score_value(proposed_sections.get(key))
        final_score = _score_value(final_sections.get(key))
        if proposed_score is not None and final_score is not None:
            delta += abs(final_score - proposed_score)

    base = int(getattr(settings, 'REVIEWER_REWARD_BASE_POINTS', 10))
    penalty = int(getattr(settings, 'REVIEWER_REWARD_PENALTY_PER_SCORE_POINT', 2))
    reward = max(0, base - penalty * delta)

    if proposed_points is not None and final_points is not None:
        if proposed_points == 0:
            factor = 1 if final_points == 0 else 0
        else:
            factor = 1 - abs(final_points - proposed_points) / proposed_points
        reward = max(0, round(reward * factor))

    return reward


def _grant_reward_contribution(user, reward_points, *, notes, title, log_ref):
    if reward_points <= 0 or not user:
        return None

    contribution_type = ContributionType.objects.filter(
        slug=REVIEWER_REWARD_TYPE_SLUG,
    ).first()
    if not contribution_type:
        logger.warning(
            "Skipping reviewer reward for %s: missing contribution type %s",
            log_ref,
            REVIEWER_REWARD_TYPE_SLUG,
        )
        return None

    from leaderboard.models import GlobalLeaderboardMultiplier

    try:
        with transaction.atomic():
            # Lock the contribution type row because multipliers are historical:
            # multiple multiplier rows per type are valid, but the default row
            # should only be auto-created once.
            contribution_type = ContributionType.objects.select_for_update().get(
                pk=contribution_type.pk,
            )
            if not GlobalLeaderboardMultiplier.objects.filter(
                contribution_type=contribution_type,
            ).exists():
                GlobalLeaderboardMultiplier.objects.create(
                    contribution_type=contribution_type,
                    multiplier_value=1.0,
                    valid_from=timezone.now() - timezone.timedelta(days=30),
                    description='Default multiplier for project review rewards',
                    notes='Auto-created when steward review rewards are granted',
                )

            clamped_points = min(
                max(int(reward_points), contribution_type.min_points),
                contribution_type.max_points,
            )
            return Contribution.objects.create(
                user=user,
                contribution_type=contribution_type,
                points=clamped_points,
                contribution_date=timezone.now(),
                notes=notes,
                title=title,
            )
    except ValidationError:
        logger.exception("Failed to grant reviewer reward for %s", log_ref)
    except Exception:
        logger.exception("Unexpected reviewer reward grant failure for %s", log_ref)
    return None


def grant_reviewer_reward(proposal, reward_points):
    if reward_points <= 0 or not proposal.proposer_id:
        return None

    return _grant_reward_contribution(
        proposal.proposer,
        reward_points,
        notes=f"Project review reward for submission {proposal.submitted_contribution_id}",
        title='Project Review Reward',
        log_ref=f"proposal {proposal.pk}",
    )


def grant_decision_reward(user, submission, action):
    notes = f"Review decision reward for submission {submission.id} [{action}]"
    contribution_type = ContributionType.objects.filter(
        slug=REVIEWER_REWARD_TYPE_SLUG,
    ).first()
    if not contribution_type:
        return None, 'unavailable'

    if Contribution.objects.filter(
        user=user,
        contribution_type=contribution_type,
        notes=notes,
    ).exists():
        return None, 'duplicate'

    reward_points = int(getattr(settings, 'REVIEWER_REWARD_BASE_POINTS', 10))
    contribution = _grant_reward_contribution(
        user,
        reward_points,
        notes=notes,
        title='Review Decision Reward',
        log_ref=f"decision on submission {submission.id} [{action}]",
    )
    if not contribution:
        return None, 'grant_failed'
    return contribution, 'granted'
