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


def compute_reviewer_reward(*, proposed_action, proposed_sections, final_action, final_sections):
    """Compute escrowed reviewer points from action match and rubric score deltas.

    Final point edits are intentionally ignored; Builder Project points derive
    from the rubric and only section-score disagreement is penalized.
    """
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
    return max(0, base - penalty * delta)


def grant_reviewer_reward(proposal, reward_points):
    if reward_points <= 0 or not proposal.proposer_id:
        return None

    contribution_type = ContributionType.objects.filter(
        slug=REVIEWER_REWARD_TYPE_SLUG,
    ).first()
    if not contribution_type:
        logger.warning(
            "Skipping reviewer reward for proposal %s: missing contribution type %s",
            proposal.pk,
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
                user=proposal.proposer,
                contribution_type=contribution_type,
                points=clamped_points,
                contribution_date=timezone.now(),
                notes=f"Project review reward for submission {proposal.submitted_contribution_id}",
                title='Project Review Reward',
            )
    except ValidationError:
        logger.exception("Failed to grant reviewer reward for proposal %s", proposal.pk)
    except Exception:
        logger.exception("Unexpected reviewer reward grant failure for proposal %s", proposal.pk)
    return None
