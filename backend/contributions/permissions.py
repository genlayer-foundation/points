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


def steward_has_permission(user, contribution_type_id, action):
    """
    Check if a steward has a specific action permission on a contribution type.
    Returns False if user is not a steward or doesn't have the permission.
    """
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
    if not hasattr(user, 'steward'):
        return []
    from stewards.models import StewardPermission
    qs = StewardPermission.objects.filter(steward=user.steward)
    if actions:
        qs = qs.filter(action__in=actions)
    return list(qs.values_list('contribution_type_id', flat=True).distinct())