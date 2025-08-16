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