"""Helpers shared by the Projects / Milestones contribution type split.

"Projects" here means the Projects contribution type (formerly "Projects &
Milestones"), not the projects app's curated Project profiles. A Milestones
submission must be linked to one of the submitter's accepted Projects
contributions and receives a sequential version number within that project
contribution.
"""
from django.db.models import Max


PROJECT_TYPE_SLUG = 'projects'
MILESTONE_TYPE_SLUG = 'milestones'


def is_milestone_contribution_type(contribution_type):
    return getattr(contribution_type, 'slug', None) == MILESTONE_TYPE_SLUG


def accepted_project_contributions_for_user(user):
    """Accepted Projects contributions the user can attach milestones to."""
    from .models import Contribution

    return Contribution.objects.filter(
        user=user,
        contribution_type__slug=PROJECT_TYPE_SLUG,
    )


def project_contribution_display_title(contribution):
    """Human-readable label for a Projects contribution in milestone pickers."""
    title = (contribution.title or '').strip()
    if title:
        return title
    notes_first_line = (contribution.notes or '').strip().splitlines()
    if notes_first_line:
        return notes_first_line[0][:200]
    return f'Project #{contribution.id}'


def project_contribution_github_url(contribution):
    """First GitHub evidence URL of a Projects contribution (the reviewed repo)."""
    for evidence in contribution.evidence_items.filter(url__gt='').order_by('created_at'):
        if 'github.com' in evidence.url.lower():
            return evidence.url
    return ''


def next_milestone_version(project_contribution, exclude_submission_id=None):
    from .models import Contribution, ContributionType, SubmittedContribution

    milestone_type_ids = ContributionType.objects.filter(
        slug=MILESTONE_TYPE_SLUG,
    ).values_list('id', flat=True)

    accepted_max = (
        Contribution.objects
        .filter(
            project_contribution=project_contribution,
            contribution_type_id__in=milestone_type_ids,
        )
        .aggregate(max_version=Max('milestone_version'))
        .get('max_version')
        or 0
    )

    pending_qs = SubmittedContribution.objects.filter(
        project_contribution=project_contribution,
        contribution_type_id__in=milestone_type_ids,
    ).exclude(state__in=['rejected', 'canceled'])
    if exclude_submission_id:
        pending_qs = pending_qs.exclude(id=exclude_submission_id)

    submitted_max = pending_qs.aggregate(
        max_version=Max('milestone_version'),
    ).get('max_version') or 0

    return max(accepted_max, submitted_max) + 1
