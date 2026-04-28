from django.db.models import Q
from rest_framework import permissions


class IsSteward(permissions.BasePermission):
    """
    Custom permission to only allow stewards to access certain views.
    """

    def has_permission(self, request, view):
        """
        Check if the user is authenticated and has a steward profile.
        """
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user has a steward profile
        return hasattr(request.user, 'steward')


# Role constants mirrored here so call sites don't have to import from stewards.
_ROLE_FULL_REVIEW = 'full_review'
_ROLE_PROPOSE = 'propose'
_PROPOSE_ACTIONS = {'propose'}
_FULL_REVIEW_ACTIONS = {'accept', 'reject', 'request_more_info', 'propose'}


def _roles_for_actions(actions):
    """
    Given an iterable of action names, return the set of assignment roles that
    satisfy *any* of them. full_review satisfies all four actions; propose
    only satisfies 'propose'.
    """
    if actions is None:
        return {_ROLE_FULL_REVIEW, _ROLE_PROPOSE}
    action_set = set(actions)
    roles = set()
    if action_set & (_FULL_REVIEW_ACTIONS - {'propose'}):
        roles.add(_ROLE_FULL_REVIEW)
    if 'propose' in action_set:
        roles.add(_ROLE_FULL_REVIEW)
        roles.add(_ROLE_PROPOSE)
    return roles


def steward_has_permission(user, contribution_type_id, action):
    """
    Check if a steward has a specific action permission on a contribution type.
    Returns False if user is not a steward or has no matching assignment.
    """
    if not hasattr(user, 'steward'):
        return False

    roles = _roles_for_actions([action])
    if not roles:
        return False

    from contributions.models import ContributionType
    from stewards.models import StewardAssignment

    category_id = (
        ContributionType.objects
        .filter(pk=contribution_type_id)
        .values_list('category_id', flat=True)
        .first()
    )

    scope_q = Q(scope_type_id=contribution_type_id) | Q(
        scope_category__isnull=True, scope_type__isnull=True
    )
    if category_id is not None:
        scope_q |= Q(scope_category_id=category_id)

    return StewardAssignment.objects.filter(
        steward=user.steward,
        role__in=roles,
    ).filter(scope_q).exists()


def steward_permitted_type_ids(user, actions=None):
    """
    Get list of contribution type IDs the steward has permission on for at
    least one of the given actions. If actions is None, returns types covered
    by any assignment.
    """
    if not hasattr(user, 'steward'):
        return []

    roles = _roles_for_actions(actions)
    if not roles:
        return []

    from contributions.models import ContributionType
    from stewards.models import StewardAssignment

    assignments = StewardAssignment.objects.filter(
        steward=user.steward,
        role__in=roles,
    )

    # Global assignment -> every contribution type.
    if assignments.filter(scope_category__isnull=True, scope_type__isnull=True).exists():
        return list(ContributionType.objects.values_list('id', flat=True))

    category_ids = set(
        assignments.filter(scope_category__isnull=False)
        .values_list('scope_category_id', flat=True)
    )
    explicit_type_ids = set(
        assignments.filter(scope_type__isnull=False)
        .values_list('scope_type_id', flat=True)
    )

    covered = set(explicit_type_ids)
    if category_ids:
        covered |= set(
            ContributionType.objects
            .filter(category_id__in=category_ids)
            .values_list('id', flat=True)
        )
    return list(covered)
