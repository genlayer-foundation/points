from rest_framework import permissions


def is_steward_superuser(user):
    """Return whether a steward should receive every steward permission."""
    return bool(
        user
        and user.is_authenticated
        and getattr(user, 'is_superuser', False)
        and hasattr(user, 'steward')
    )


def effective_steward_tier(user):
    """Return the user's effective steward tier, or zero for non-stewards."""
    if not (
        user
        and user.is_authenticated
        and hasattr(user, 'steward')
    ):
        return 0
    if is_steward_superuser(user):
        return 3
    return user.steward.tier


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


def steward_has_permission(user, contribution_type_id, action):
    """
    Check if a steward has a specific action permission on a contribution type.
    Returns False if user is not a steward or doesn't have the permission.
    """
    if is_steward_superuser(user) or effective_steward_tier(user) >= 2:
        return True
    if not hasattr(user, 'steward'):
        return False
    from stewards.models import StewardPermission
    return StewardPermission.objects.filter(
        steward=user.steward,
        contribution_type_id=contribution_type_id,
        action=action,
    ).exists()


def steward_permitted_type_ids(user, actions=None):
    """
    Get list of contribution type IDs the steward has permissions on.
    If actions is provided, only return types where the steward has at least one of those actions.
    If actions is None, return types where the steward has any permission.
    """
    if is_steward_superuser(user) or effective_steward_tier(user) >= 2:
        from contributions.models import ContributionType
        return list(ContributionType.objects.values_list('id', flat=True))
    if not hasattr(user, 'steward'):
        return []
    from stewards.models import StewardPermission
    qs = StewardPermission.objects.filter(steward=user.steward)
    if actions:
        qs = qs.filter(action__in=actions)
    return list(qs.values_list('contribution_type_id', flat=True).distinct())


def steward_permission_map(user):
    """Return the effective per-type steward permissions for a user."""
    from stewards.models import StewardPermission

    if is_steward_superuser(user) or effective_steward_tier(user) >= 2:
        from contributions.models import ContributionType

        actions = [choice[0] for choice in StewardPermission.ACTION_CHOICES]
        return {
            str(contribution_type_id): list(actions)
            for contribution_type_id in ContributionType.objects.values_list('id', flat=True)
        }

    if not hasattr(user, 'steward'):
        return {}

    result = {}
    permissions_qs = StewardPermission.objects.filter(
        steward=user.steward,
    ).values_list('contribution_type_id', 'action')
    for contribution_type_id, action in permissions_qs:
        result.setdefault(str(contribution_type_id), []).append(action)
    return result
