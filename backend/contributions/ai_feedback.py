import re
from collections.abc import Mapping
from numbers import Integral
from urllib.parse import quote, urlparse

import requests
from django.conf import settings
from rest_framework import serializers

from .ai_attribution import AI_STEWARD_EMAIL
from .models import ReviewProposal, SubmissionNote
from .rubric_review import RUBRIC_GATE_FAILURES, RUBRIC_SECTIONS


FEEDBACK_VERDICTS = (
    'agree',
    'agree_with_corrections',
    'disagree',
)
FEEDBACK_DECISIONS = (
    'accept',
    'reject',
    'more_info',
    'skip',
)
ERROR_CLAIM_TYPES = (
    'factual_error',
    'missed_issue',
    'missed_strength',
    'wrong_weight',
    'access_error',
)
CLAIM_ANCHORS = (*RUBRIC_SECTIONS.keys(), 'synthesis')

_FEEDBACK_KEYS = {
    'verdict',
    'correct_decision',
    'gate_failures',
    'criteria',
    'error_claims',
}
_CORRECTION_KEYS = {'range', 'reason'}
_AGREEMENT_KEYS = {'agree'}
_CLAIM_KEYS = {'type', 'text', 'evidence_ref', 'anchor'}
_COMMIT_SHA_RE = re.compile(r'^[0-9a-f]{40}$')


def _unknown_keys_error(field_name, keys):
    unknown = ', '.join(sorted(str(key) for key in keys))
    return serializers.ValidationError({field_name: f'Unknown key(s): {unknown}.'})


def _normalize_gate_failures(value):
    if not isinstance(value, list):
        raise serializers.ValidationError({'gate_failures': 'Must be a list.'})

    normalized = []
    invalid = []
    for gate_failure in value:
        if not isinstance(gate_failure, str) or gate_failure not in RUBRIC_GATE_FAILURES:
            invalid.append(gate_failure)
        elif gate_failure not in normalized:
            normalized.append(gate_failure)

    if invalid:
        values = ', '.join(str(item) for item in invalid)
        raise serializers.ValidationError({
            'gate_failures': f'Unknown value(s): {values}.',
        })
    return normalized


def _normalize_criteria(value):
    if not isinstance(value, Mapping):
        raise serializers.ValidationError({'criteria': 'Must be an object.'})

    unknown_sections = set(value) - set(RUBRIC_SECTIONS)
    if unknown_sections:
        raise _unknown_keys_error('criteria', unknown_sections)

    normalized = {}
    for section, criterion in value.items():
        if not isinstance(criterion, Mapping):
            raise serializers.ValidationError({
                'criteria': {section: 'Must be an object.'},
            })

        keys = set(criterion)
        if keys == _AGREEMENT_KEYS:
            if criterion['agree'] is not True:
                raise serializers.ValidationError({
                    'criteria': {section: 'Agreement must be exactly {"agree": true}.'},
                })
            normalized[section] = {'agree': True}
            continue

        if keys != _CORRECTION_KEYS:
            unknown = keys - (_AGREEMENT_KEYS | _CORRECTION_KEYS)
            if unknown:
                raise serializers.ValidationError({
                    'criteria': {section: f"Unknown key(s): {', '.join(sorted(map(str, unknown)))}."},
                })
            raise serializers.ValidationError({
                'criteria': {
                    section: (
                        'Must be exactly {"agree": true} or '
                        '{"range": [min, max], "reason": string}.'
                    ),
                },
            })

        score_range = criterion['range']
        if (
            not isinstance(score_range, list)
            or len(score_range) != 2
            or any(
                isinstance(score, bool) or not isinstance(score, Integral)
                for score in score_range
            )
        ):
            raise serializers.ValidationError({
                'criteria': {section: 'Range must contain exactly two integer scores.'},
            })

        minimum, maximum = (int(score) for score in score_range)
        if minimum < 0 or maximum > 5 or minimum > maximum:
            raise serializers.ValidationError({
                'criteria': {section: 'Range must satisfy 0 <= min <= max <= 5.'},
            })

        reason = criterion['reason']
        if not isinstance(reason, str):
            raise serializers.ValidationError({
                'criteria': {section: 'Reason must be a string.'},
            })
        reason = reason.strip()
        if len(reason) > 500:
            raise serializers.ValidationError({
                'criteria': {section: 'Reason must be at most 500 characters.'},
            })

        normalized[section] = {
            'range': [minimum, maximum],
            'reason': reason,
        }

    return normalized


def _normalize_error_claims(value):
    if not isinstance(value, list):
        raise serializers.ValidationError({'error_claims': 'Must be a list.'})

    normalized = []
    for index, claim in enumerate(value):
        if not isinstance(claim, Mapping):
            raise serializers.ValidationError({
                'error_claims': {index: 'Must be an object.'},
            })

        unknown = set(claim) - _CLAIM_KEYS
        if unknown:
            raise serializers.ValidationError({
                'error_claims': {
                    index: f"Unknown key(s): {', '.join(sorted(map(str, unknown)))}.",
                },
            })

        claim_type = claim.get('type')
        if claim_type not in ERROR_CLAIM_TYPES:
            raise serializers.ValidationError({
                'error_claims': {index: 'Unknown claim type.'},
            })

        text = claim.get('text')
        if not isinstance(text, str) or not text.strip():
            raise serializers.ValidationError({
                'error_claims': {index: 'Text is required.'},
            })
        text = text.strip()
        if len(text) > 500:
            raise serializers.ValidationError({
                'error_claims': {index: 'Text must be at most 500 characters.'},
            })

        evidence_ref = claim.get('evidence_ref', '')
        if not isinstance(evidence_ref, str):
            raise serializers.ValidationError({
                'error_claims': {index: 'Evidence reference must be a string.'},
            })
        evidence_ref = evidence_ref.strip()
        if len(evidence_ref) > 300:
            raise serializers.ValidationError({
                'error_claims': {
                    index: 'Evidence reference must be at most 300 characters.',
                },
            })

        normalized_claim = {
            'type': claim_type,
            'text': text,
            'evidence_ref': evidence_ref,
        }
        if 'anchor' in claim:
            anchor = claim['anchor']
            if anchor not in CLAIM_ANCHORS:
                raise serializers.ValidationError({
                    'error_claims': {index: 'Unknown claim anchor.'},
                })
            normalized_claim['anchor'] = anchor

        normalized.append(normalized_claim)

    return normalized


def normalize_feedback_payload(payload):
    """Validate and normalize one reviewer's opinion of an AI proposal."""
    if not isinstance(payload, Mapping):
        raise serializers.ValidationError({'detail': 'Feedback must be an object.'})

    unknown = set(payload) - _FEEDBACK_KEYS
    if unknown:
        raise _unknown_keys_error('feedback', unknown)

    verdict = payload.get('verdict')
    if verdict not in FEEDBACK_VERDICTS:
        raise serializers.ValidationError({'verdict': 'Unknown feedback verdict.'})

    raw_correct_decision = payload.get('correct_decision', '')
    if raw_correct_decision is None or raw_correct_decision == '':
        correct_decision = ''
    elif not isinstance(raw_correct_decision, str):
        raise serializers.ValidationError({'correct_decision': 'Must be a string.'})
    else:
        correct_decision = raw_correct_decision
    if correct_decision and correct_decision not in FEEDBACK_DECISIONS:
        raise serializers.ValidationError({'correct_decision': 'Unknown decision.'})

    gate_failures = _normalize_gate_failures(payload.get('gate_failures', []))
    criteria = _normalize_criteria(payload.get('criteria', {}))
    error_claims = _normalize_error_claims(payload.get('error_claims', []))

    if verdict == 'disagree':
        if not correct_decision:
            raise serializers.ValidationError({
                'correct_decision': 'A corrected decision is required when disagreeing.',
            })
    elif correct_decision:
        raise serializers.ValidationError({
            'correct_decision': 'A corrected decision is only allowed when disagreeing.',
        })

    if gate_failures and correct_decision != 'reject':
        raise serializers.ValidationError({
            'gate_failures': 'Gate failures are only allowed when correcting the decision to reject.',
        })

    has_score_correction = any('range' in criterion for criterion in criteria.values())
    has_correction = has_score_correction or bool(error_claims)
    if verdict == 'agree' and has_correction:
        raise serializers.ValidationError({
            'verdict': 'Agree feedback cannot include corrections or error claims.',
        })
    if verdict == 'agree_with_corrections' and not has_correction:
        raise serializers.ValidationError({
            'verdict': 'At least one score correction or error claim is required.',
        })

    return {
        'verdict': verdict,
        'correct_decision': correct_decision,
        'gate_failures': gate_failures,
        'criteria': criteria,
        'error_claims': error_claims,
    }


def resolve_proposal_binding(submission, review_proposal_id=None):
    """Bind feedback to an explicit or latest durable AI proposal snapshot."""
    if review_proposal_id is not None:
        try:
            proposal = ReviewProposal.objects.get(
                pk=review_proposal_id,
                submitted_contribution=submission,
                source=ReviewProposal.SOURCE_AI,
            )
        except ReviewProposal.DoesNotExist as exc:
            raise serializers.ValidationError({
                'review_proposal_id': 'AI review proposal not found for this submission.',
            }) from exc
        return proposal, proposal.created_at

    proposal = (
        ReviewProposal.objects
        .filter(
            submitted_contribution=submission,
            source=ReviewProposal.SOURCE_AI,
        )
        .order_by('-created_at', '-id')
        .first()
    )
    if proposal:
        return proposal, proposal.created_at

    proposal_note = (
        SubmissionNote.objects
        .filter(
            submitted_contribution=submission,
            is_proposal=True,
            user__email=AI_STEWARD_EMAIL,
        )
        .order_by('-created_at', '-id')
        .first()
    )
    if proposal_note:
        return None, proposal_note.created_at

    raise serializers.ValidationError({'detail': 'No AI proposal found for this submission.'})


def _github_repository_from_url(url):
    try:
        parsed = urlparse(url)
    except (TypeError, ValueError):
        return None

    if (parsed.hostname or '').lower() not in {'github.com', 'www.github.com'}:
        return None

    parts = [part for part in parsed.path.split('/') if part]
    if len(parts) < 2:
        return None

    owner, repository = parts[:2]
    if repository.endswith('.git'):
        repository = repository[:-4]
    if not owner or not repository:
        return None
    return owner, repository


def fetch_reviewed_commit_sha(submission):
    """Resolve the reviewed repository HEAD; failures never block feedback."""
    try:
        repository = None
        evidence_urls = (
            submission.evidence_items
            .exclude(url='')
            .order_by('created_at', 'id')
            .values_list('url', flat=True)
        )
        for url in evidence_urls:
            repository = _github_repository_from_url(url)
            if repository:
                break
        if not repository:
            return ''

        owner, repo = repository
        headers = {'Accept': 'application/vnd.github.sha'}
        token = getattr(settings, 'GITHUB_METRICS_TOKEN', '')
        if token:
            headers['Authorization'] = f'Bearer {token}'

        response = requests.get(
            'https://api.github.com/repos/'
            f'{quote(owner, safe="")}/{quote(repo, safe="")}/commits/HEAD',
            headers=headers,
            timeout=5,
        )
        sha = response.text.strip() if response.status_code == 200 else ''
        return sha if _COMMIT_SHA_RE.fullmatch(sha) else ''
    except Exception:
        return ''
