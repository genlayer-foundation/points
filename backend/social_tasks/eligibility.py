from dataclasses import dataclass

from django.core.exceptions import ValidationError


SUPPORTED_RULE_TYPES = {
    'accepted_submittable_contribution',
    'community_points',
}
SUPPORTED_COMMUNITY_POINT_SOURCES = {'effective', 'portal'}


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    message: str = ''
    details: dict | None = None


def validate_eligibility_requirements(value):
    """Validate SocialTask.eligibility_requirements.

    Supported shapes:
    - {}: no gate
    - {"type": "..."}: one required rule
    - {"all": [{...}], "any": [{...}]}: all `all` rules and one `any` rule
    - [{...}, {...}]: shorthand for {"all": [...]}
    """
    normalized = _normalize_requirements(value)
    for group_name in ('all', 'any'):
        for rule in normalized[group_name]:
            _validate_rule(rule)


def evaluate_task_eligibility(task, user):
    # Validator tasks can award validator leaderboard points. Portal viewing
    # exceptions must never become an alternate path to earning those points.
    if getattr(getattr(task, 'category', None), 'slug', None) == 'validator':
        if user is None or not getattr(user, 'is_authenticated', False):
            return EligibilityResult(
                False,
                'Sign in with a validator account to complete this task.',
                details={'requirements': [], 'required_role': 'validator'},
            )

        from validators.models import user_has_validator_profile
        if not user_has_validator_profile(user):
            return EligibilityResult(
                False,
                'Only validators can complete validator tasks.',
                details={'requirements': [], 'required_role': 'validator'},
            )

    requirements = task.eligibility_requirements or {}
    normalized = _normalize_requirements(requirements)
    rules = normalized['all'] + normalized['any']
    if not rules:
        return EligibilityResult(True, details={'requirements': []})

    if user is None or not getattr(user, 'is_authenticated', False):
        return EligibilityResult(
            False,
            'Sign in to check this task requirement.',
            details={'requirements': []},
        )

    all_results = [_evaluate_rule(rule, task, user) for rule in normalized['all']]
    any_results = [_evaluate_rule(rule, task, user) for rule in normalized['any']]

    all_ok = all(result['eligible'] for result in all_results)
    any_ok = True if not any_results else any(result['eligible'] for result in any_results)
    eligible = all_ok and any_ok

    message = ''
    if not eligible:
        message = requirements.get('message') if isinstance(requirements, dict) else ''
        if not message:
            failed_all = [result for result in all_results if not result['eligible']]
            if failed_all:
                message = failed_all[0]['message']
            elif any_results:
                message = 'Meet one of this task\'s requirements first.'

    return EligibilityResult(
        eligible,
        message,
        details={
            'requirements': all_results + any_results,
            'mode': {
                'all': len(all_results),
                'any': len(any_results),
            },
        },
    )


def _normalize_requirements(value):
    if value in (None, '', {}):
        return {'all': [], 'any': []}
    if isinstance(value, list):
        return {'all': value, 'any': []}
    if not isinstance(value, dict):
        raise ValidationError({
            'eligibility_requirements': 'Expected an object, a list of rules, or an empty value.'
        })
    if 'type' in value:
        return {'all': [value], 'any': []}

    unknown_keys = set(value) - {'all', 'any', 'message'}
    if unknown_keys:
        raise ValidationError({
            'eligibility_requirements': f'Unknown key(s): {", ".join(sorted(unknown_keys))}.'
        })

    all_rules = value.get('all', [])
    any_rules = value.get('any', [])
    if not isinstance(all_rules, list) or not isinstance(any_rules, list):
        raise ValidationError({
            'eligibility_requirements': '`all` and `any` must be lists of rule objects.'
        })
    return {'all': all_rules, 'any': any_rules}


def _validate_rule(rule):
    if not isinstance(rule, dict):
        raise ValidationError({
            'eligibility_requirements': 'Each eligibility rule must be an object.'
        })
    rule_type = rule.get('type')
    if rule_type not in SUPPORTED_RULE_TYPES:
        raise ValidationError({
            'eligibility_requirements': (
                f'Unknown eligibility rule type: {rule_type!r}. '
                f'Use one of: {", ".join(sorted(SUPPORTED_RULE_TYPES))}.'
            )
        })

    minimum = rule.get('minimum', 1)
    if not isinstance(minimum, int) or minimum < 1:
        raise ValidationError({
            'eligibility_requirements': 'Eligibility rule `minimum` must be a positive integer.'
        })

    if rule_type == 'accepted_submittable_contribution':
        category = rule.get('category', 'task')
        if not isinstance(category, str) or not category:
            raise ValidationError({
                'eligibility_requirements': 'Contribution eligibility `category` must be a slug or "task".'
            })
        if 'submittable' in rule and not isinstance(rule['submittable'], bool):
            raise ValidationError({
                'eligibility_requirements': 'Contribution eligibility `submittable` must be true or false.'
            })

    if rule_type == 'community_points':
        source = rule.get('source', 'effective')
        if source not in SUPPORTED_COMMUNITY_POINT_SOURCES:
            raise ValidationError({
                'eligibility_requirements': (
                    'Community points `source` must be "effective" or "portal".'
                )
            })


def _evaluate_rule(rule, task, user):
    rule_type = rule['type']
    if rule_type == 'accepted_submittable_contribution':
        return _accepted_submittable_contribution_result(rule, task, user)
    if rule_type == 'community_points':
        return _community_points_result(rule, user)
    return {
        'type': rule_type,
        'eligible': False,
        'message': 'Unsupported task requirement.',
    }


def _accepted_submittable_contribution_result(rule, task, user):
    from contributions.models import Contribution

    category = rule.get('category', 'task')
    category_slug = task.category.slug if category == 'task' else category
    minimum = rule.get('minimum', 1)
    submittable = rule.get('submittable', True)

    filters = {
        'user': user,
        'contribution_type__category__slug': category_slug,
    }
    if submittable:
        filters['contribution_type__is_submittable'] = True

    count = Contribution.objects.filter(**filters).count()
    label = category_slug.replace('-', ' ')
    return {
        'type': 'accepted_submittable_contribution',
        'category': category_slug,
        'minimum': minimum,
        'current': count,
        'eligible': count >= minimum,
        'message': f'Complete at least {minimum} accepted {label} contribution first.',
    }


def _community_points_result(rule, user):
    minimum = rule.get('minimum', 1)
    source = rule.get('source', 'effective')
    if source == 'portal':
        from leaderboard.models import calculate_category_points
        current = calculate_category_points(user, 'community')
    else:
        from community_xp.utils import get_effective_community_points
        current = get_effective_community_points(user)['total_points']

    return {
        'type': 'community_points',
        'source': source,
        'minimum': minimum,
        'current': current,
        'eligible': current >= minimum,
        'message': f'Earn at least {minimum} community points first.',
    }
