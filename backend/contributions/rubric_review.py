import decimal
from numbers import Integral

from rest_framework import serializers

from .models import ContributionType


PROJECT_REVIEW_FLOWS = {
    ContributionType.REVIEW_FLOW_BUILDER_PROJECT,
}

RUBRIC_SECTIONS = {
    'genlayer_fit': 'GenLayer fit',
    'contract_quality': 'Contract quality',
    'engineering': 'Engineering',
    'frontend_ux': 'Frontend / UX',
}

RUBRIC_EXTRAS = {
    'live_deployment': 'Live deployment',
    'demo_video': 'Demo video',
    'public_post': 'Public post',
}

RUBRIC_GATE_FAILURES = {
    'no_real_genlayer_contract': 'No real GenLayer contract or fake/off-chain AI consensus',
    'branding_only': 'GenLayer is only branding and nothing actually calls a contract',
    'repo_does_not_build': 'Repository does not build or work',
    'empty_fork_or_boilerplate': 'Empty, plain fork, or renamed boilerplate example',
}


def uses_project_rubric(contribution_type):
    return (
        contribution_type
        and contribution_type.review_flow in PROJECT_REVIEW_FLOWS
    )


def _unique_valid_list(values, valid_keys, field_name):
    if values is None:
        return []
    if not isinstance(values, list):
        raise serializers.ValidationError({
            field_name: 'Must be a list.'
        })

    normalized = []
    invalid = []
    seen = set()
    for value in values:
        if value not in valid_keys:
            invalid.append(value)
            continue
        if value not in seen:
            normalized.append(value)
            seen.add(value)

    if invalid:
        raise serializers.ValidationError({
            field_name: f"Unknown value(s): {', '.join(map(str, invalid))}."
        })
    return normalized


def _score_error(section_key, message='Score must be a number from 0 to 5.'):
    return serializers.ValidationError({
        'sections': {section_key: message}
    })


def _normalize_score(value, section_key):
    if isinstance(value, bool):
        raise _score_error(section_key)

    if isinstance(value, Integral):
        score = int(value)
    elif isinstance(value, str):
        stripped = value.strip()
        digits = stripped[1:] if stripped.startswith('-') else stripped
        if not digits.isdigit():
            raise _score_error(section_key)
        score = int(stripped)
    elif isinstance(value, float):
        if not value.is_integer():
            raise _score_error(section_key)
        score = int(value)
    elif isinstance(value, decimal.Decimal):
        if not value.is_finite() or value != value.to_integral_value():
            raise _score_error(section_key)
        score = int(value)
    else:
        raise serializers.ValidationError({
            'sections': {section_key: 'Score must be a number from 0 to 5.'}
        })

    if score < 0 or score > 5:
        raise serializers.ValidationError({
            'sections': {section_key: 'Score must be between 0 and 5.'}
        })
    return score


def normalize_rubric_review_payload(
    payload,
    proposed_action,
    require_overall_reason=True,
    action_field='proposed_action',
):
    if payload is None:
        raise serializers.ValidationError({
            'rubric_review': 'Rubric review is required for Builder Project reviews.'
        })
    if not isinstance(payload, dict):
        raise serializers.ValidationError({
            'rubric_review': 'Must be an object.'
        })

    gate_failures = _unique_valid_list(
        payload.get('gate_failures', []),
        RUBRIC_GATE_FAILURES,
        'gate_failures',
    )
    extras = _unique_valid_list(
        payload.get('extras', []),
        RUBRIC_EXTRAS,
        'extras',
    )
    overall_reason = str(payload.get('overall_reason') or '').strip()
    if require_overall_reason and not overall_reason:
        raise serializers.ValidationError({
            'overall_reason': 'Overall reason is required.'
        })

    if gate_failures:
        if proposed_action != 'reject':
            raise serializers.ValidationError({
                action_field: 'Gate failures must be submitted as reject reviews.'
            })
        return {
            'gate_failures': gate_failures,
            'sections': {},
            'extras': extras,
            'overall_reason': overall_reason,
        }

    raw_sections = payload.get('sections')
    if not isinstance(raw_sections, dict):
        raise serializers.ValidationError({
            'sections': 'All rubric sections are required when the gate passes.'
        })

    sections = {}
    section_errors = {}
    for key in RUBRIC_SECTIONS:
        raw_section = raw_sections.get(key)
        if not isinstance(raw_section, dict):
            section_errors[key] = 'Section score is required.'
            continue

        try:
            score = _normalize_score(raw_section.get('score'), key)
        except serializers.ValidationError as exc:
            section_errors[key] = exc.detail.get('sections', {}).get(key, str(exc.detail))
            continue

        sections[key] = {
            'score': score,
            'reason': str(raw_section.get('reason') or '').strip(),
        }

    if section_errors:
        raise serializers.ValidationError({'sections': section_errors})

    return {
        'gate_failures': [],
        'sections': sections,
        'extras': extras,
        'overall_reason': overall_reason,
    }


def rubric_summary_text(rubric_review):
    if not rubric_review:
        return ''

    gate_failures = rubric_review.get('gate_failures') or []
    if gate_failures:
        labels = [
            RUBRIC_GATE_FAILURES.get(key, key)
            for key in gate_failures
        ]
        return f"Gate failed: {', '.join(labels)}."

    sections = rubric_review.get('sections') or {}
    score_parts = []
    for key, label in RUBRIC_SECTIONS.items():
        section = sections.get(key) or {}
        if 'score' in section:
            score_parts.append(f"{label} {section['score']}/5")

    extras = rubric_review.get('extras') or []
    extra_text = ''
    if extras:
        extra_labels = [RUBRIC_EXTRAS.get(key, key) for key in extras]
        extra_text = f" Extras: {', '.join(extra_labels)}."

    return f"Rubric scores: {', '.join(score_parts)}.{extra_text}"
