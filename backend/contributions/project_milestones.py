"""Helpers shared by the Projects / Milestones contribution type split.

Projects submissions create a Project profile when accepted; Milestones
submissions must be linked to one of the submitter's accepted projects and
receive a sequential version number within that project.
"""
from django.db.models import Max, Q

from projects.models import Project


PROJECT_TYPE_SLUG = 'projects'
LEGACY_PROJECT_TYPE_SLUGS = {
    PROJECT_TYPE_SLUG,
    'projects-and-milestones',
    'projects-milestones',
    'project-milestone',
}
MILESTONE_TYPE_SLUG = 'milestones'


def is_project_contribution_type(contribution_type):
    slug = getattr(contribution_type, 'slug', None)
    name = (getattr(contribution_type, 'name', '') or '').strip().lower()
    return slug in LEGACY_PROJECT_TYPE_SLUGS or name in {
        'projects',
        'projects and milestones',
        'project and milestone',
    }


def is_milestone_contribution_type(contribution_type):
    return getattr(contribution_type, 'slug', None) == MILESTONE_TYPE_SLUG


def accepted_projects_for_user(user):
    """Active projects the user can attach milestones to.

    Acceptance is proven through the stable Contribution.project FK rather
    than Project.related_contributions, which is editable profile data.
    """
    return (
        Project.objects
        .filter(status=Project.STATUS_ACTIVE)
        .filter(Q(user=user) | Q(participants=user))
        .filter(contributions__contribution_type__slug=PROJECT_TYPE_SLUG)
        .distinct()
    )


def next_milestone_version(project, exclude_submission_id=None):
    from .models import Contribution, ContributionType, SubmittedContribution

    milestone_type_ids = ContributionType.objects.filter(
        slug=MILESTONE_TYPE_SLUG,
    ).values_list('id', flat=True)

    accepted_max = (
        Contribution.objects
        .filter(project=project, contribution_type_id__in=milestone_type_ids)
        .aggregate(max_version=Max('milestone_version'))
        .get('max_version')
        or 0
    )

    pending_qs = SubmittedContribution.objects.filter(
        project=project,
        contribution_type_id__in=milestone_type_ids,
    ).exclude(state__in=['rejected', 'canceled'])
    if exclude_submission_id:
        pending_qs = pending_qs.exclude(id=exclude_submission_id)

    submitted_max = pending_qs.aggregate(
        max_version=Max('milestone_version'),
    ).get('max_version') or 0

    return max(accepted_max, submitted_max) + 1
