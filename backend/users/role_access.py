"""Server-authoritative helpers for non-steward role section access."""

from django.apps import apps


VIEWABLE_ROLE_CATEGORIES = frozenset({'builder', 'validator', 'community'})
_ROLE_PROFILE_MODELS = {
    'builder': ('builders', 'Builder'),
    'validator': ('validators', 'Validator'),
    'community': ('creators', 'Creator'),
}


def user_has_role_profile(user, category):
    """Return whether the user holds the real profile for a portal role."""
    user_id = getattr(user, 'pk', None)
    if not user_id or category not in VIEWABLE_ROLE_CATEGORIES:
        return False

    cache = getattr(user, '_role_profile_access_cache', None)
    if cache is None:
        cache = {}
        setattr(user, '_role_profile_access_cache', cache)
    if category not in cache:
        app_label, model_name = _ROLE_PROFILE_MODELS[category]
        model = apps.get_model(app_label, model_name)
        cache[category] = model.objects.filter(user_id=user_id).exists()
    return cache[category]


def user_can_view_role_sections(user):
    """Return whether admin enabled the non-steward read-only viewer flag."""
    return bool(
        user
        and getattr(user, 'is_authenticated', False)
        and getattr(user, 'can_view_role_sections', False)
    )


def can_view_role_section(user, category):
    """Authorize a gated non-steward section for a member or admin-enabled viewer."""
    if category not in VIEWABLE_ROLE_CATEGORIES:
        return False
    return user_has_role_profile(user, category) or user_can_view_role_sections(user)


def is_role_section_read_only(user, category):
    """Return whether access to this category comes only from the viewer flag."""
    return bool(
        category in VIEWABLE_ROLE_CATEGORIES
        and user_can_view_role_sections(user)
        and not user_has_role_profile(user, category)
    )
