from rest_framework.permissions import BasePermission

from .models import ServiceAccountToken


class HasServiceAccountScope(BasePermission):
    """Check the authenticated token against the view's `required_scopes` map.

    Views declare which scope each action needs, with '*' as the default:

        required_scopes = {'write_action': 'myfeature:write', '*': 'myfeature:read'}

    Configuration lives on the view (not constructor args) so DRF `|`
    permission composition works.
    """

    def has_permission(self, request, view):
        token = request.auth
        if not isinstance(token, ServiceAccountToken):
            return False
        scope_map = getattr(view, 'required_scopes', None) or {}
        required = scope_map.get(getattr(view, 'action', None)) or scope_map.get('*')
        return bool(required) and token.has_scope(required)
