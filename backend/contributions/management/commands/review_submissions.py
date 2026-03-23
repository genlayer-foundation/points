"""
AI-assisted submission review management command.

Processes pending submissions through two tiers:
  Tier 1: Deterministic rules (auto-reject with 100% confidence)
  Tier 2: AI classification via OpenRouter/Claude (propose for human review)

Usage:
    # Dry run - see what would happen without making changes
    python manage.py review_submissions --dry-run

    # Tier 1 only - deterministic rules
    python manage.py review_submissions --tier1-only

    # Tier 2 only - AI classification (skips tier 1)
    python manage.py review_submissions --tier2-only

    # Full run with batch size
    python manage.py review_submissions --batch-size 50

    # Filter by contribution type
    python manage.py review_submissions --type "Educational Content"

    # Process a specific submission
    python manage.py review_submissions --submission-id <uuid>

Environment:
    OPENROUTER_API_KEY: Required for Tier 2 AI classification
"""

import json
import logging
import os
import re
import time
from collections import defaultdict

import requests as http_requests
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from contributions.models import (
    ContributionType,
    SubmissionNote,
    SubmittedContribution,
)
from stewards.models import ReviewTemplate, Steward, StewardPermission
from users.models import User

logger = logging.getLogger(__name__)

AI_STEWARD_EMAIL = 'genlayer-steward@genlayer.foundation'
AI_STEWARD_NAME = 'GenLayer Steward'

OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'
OPENROUTER_MODEL = 'anthropic/claude-opus-4.6'

# Pricing per million tokens (USD) - for cost tracking
MODEL_PRICING = {
    'anthropic/claude-opus-4.6': {'input': 5.0, 'output': 25.0},
    'anthropic/claude-sonnet-4.6': {'input': 3.0, 'output': 15.0},
    'anthropic/claude-haiku-4.5': {'input': 1.0, 'output': 5.0},
}


# ─── Tier 1 Rules ────────────────────────────────────────────────────────────
# Each rule returns (template_label, crm_reason) or None if it doesn't match.
# Rules are evaluated in order; first match wins.

SPAM_NOTES = {
    'nothing', 'good', 'ok', 'okey', 'yes', 'no', 'gm', 'gn', 'lfg',
    'vvv', 'ccc', 'bio', 'bye', 'sexy girl', 'fgn', 'cxcx', 'hi',
    'hello', 'test', 'airdrop', 'free',
}


def rule_no_evidence_no_notes(submission, evidence_items):
    """Empty submission: no evidence AND no meaningful notes."""
    has_evidence = len(evidence_items) > 0
    notes = (submission.notes or '').strip()
    if not has_evidence and len(notes) == 0:
        return (
            'Reject: No Evidence',
            'Tier 1 auto-reject: No evidence and no notes provided.',
        )
    return None


def rule_no_evidence_short_notes(submission, evidence_items):
    """No evidence with very short notes (< 10 chars)."""
    has_evidence = len(evidence_items) > 0
    notes = (submission.notes or '').strip()
    if not has_evidence and 0 < len(notes) <= 10:
        return (
            'Reject: No Evidence',
            f'Tier 1 auto-reject: No evidence and notes too short '
            f'({len(notes)} chars): "{notes}"',
        )
    return None


def rule_spam_notes(submission, evidence_items):
    """Notes match known spam/gibberish patterns."""
    notes = (submission.notes or '').strip().lower()
    if notes in SPAM_NOTES:
        return (
            'Reject: Unintelligible Notes',
            f'Tier 1 auto-reject: Notes match spam pattern: "{notes}"',
        )
    # Check for purely numeric / random character notes
    if len(notes) <= 15 and re.match(r'^[^a-zA-Z]*$', notes) and len(notes) > 0:
        return (
            'Reject: Unintelligible Notes',
            f'Tier 1 auto-reject: Notes are non-alphabetic gibberish: "{notes}"',
        )
    return None


def rule_duplicate_pending_from_same_user(submission, evidence_items):
    """Same user already has an older pending submission with identical notes.

    When duplicates exist, keep the one with the most evidence.
    If the current submission has evidence but the older duplicate doesn't,
    skip rejecting this one (the evidence-less duplicate will be caught
    when processed separately).
    """
    notes = (submission.notes or '').strip()
    if not notes:
        return None  # Handled by other rules

    from contributions.models import Evidence

    # Find older pending submissions with the same notes
    older_duplicates = (
        SubmittedContribution.objects
        .filter(
            user=submission.user,
            notes=submission.notes,
            state='pending',
            created_at__lt=submission.created_at,
        )
    )
    if not older_duplicates.exists():
        return None

    # Check if the current submission has evidence
    current_has_evidence = len(evidence_items) > 0

    if current_has_evidence:
        # This submission has evidence — check if ALL older duplicates also
        # have evidence. If any older duplicate lacks evidence, don't reject
        # this one (the better submission should survive).
        for older in older_duplicates:
            older_has_evidence = Evidence.objects.filter(
                submitted_contribution=older,
                url__gt='',
            ).exists()
            if not older_has_evidence:
                # Older duplicate has no evidence but we do — skip rejection
                return None

    return (
        'Reject: Duplicate Submission',
        f'Tier 1 auto-reject: Duplicate of an older pending submission '
        f'from the same user with identical notes.',
    )


def rule_resubmitted_rejected_url(submission, evidence_items):
    """Same user resubmits a URL that was already rejected."""
    if not evidence_items:
        return None

    urls = [e.url for e in evidence_items if e.url]
    if not urls:
        return None

    from contributions.models import Evidence
    # Check if any URL was previously rejected for this same user
    rejected_url = (
        Evidence.objects
        .filter(
            url__in=urls,
            submitted_contribution__user=submission.user,
            submitted_contribution__state='rejected',
        )
        .values_list('url', flat=True)
        .first()
    )
    if rejected_url:
        return (
            'Reject: Duplicate Submission',
            f'Tier 1 auto-reject: URL was previously rejected for this user: '
            f'{rejected_url[:100]}',
        )
    return None


def rule_same_url_reused_by_same_user(submission, evidence_items):
    """Same user submitted the same URL in another pending submission."""
    if not evidence_items:
        return None

    urls = [e.url for e in evidence_items if e.url]
    if not urls:
        return None

    from contributions.models import Evidence
    # Check if any URL appears in an older pending submission by this user
    older_with_same_url = (
        Evidence.objects
        .filter(
            url__in=urls,
            submitted_contribution__user=submission.user,
            submitted_contribution__state='pending',
            submitted_contribution__created_at__lt=submission.created_at,
        )
        .exclude(submitted_contribution=submission)
        .values_list('url', flat=True)
        .first()
    )
    if older_with_same_url:
        return (
            'Reject: Duplicate Submission',
            f'Tier 1 auto-reject: Same URL already used in an older pending '
            f'submission by this user: {older_with_same_url[:100]}',
        )
    return None


# Generic platform URL prefixes that are not valid evidence
BLOCKLISTED_URL_PREFIXES = [
    'https://studio.genlayer.com/run-debug',
    'https://studio.genlayer.com/contracts',
    'https://points.genlayer.foundation',
    'https://www.genlayer.com',
    'https://genlayer.com',
]


def _is_blocklisted_url(url):
    """Check if URL matches a blocklisted platform prefix."""
    normalized = url.split('?')[0].split('#')[0].rstrip('/')
    for prefix in BLOCKLISTED_URL_PREFIXES:
        if normalized == prefix or normalized.startswith(prefix + '/'):
            return True
    return False


def rule_blocklisted_evidence_url(submission, evidence_items):
    """Evidence URL is a generic platform page, not actual work."""
    if not evidence_items:
        return None

    urls = [e.url for e in evidence_items if e.url]
    blocklisted_urls = [u for u in urls if _is_blocklisted_url(u)]
    if blocklisted_urls and len(blocklisted_urls) == len(urls):
        # ALL evidence URLs are blocklisted
        return (
            'Reject: No Evidence',
            f'Tier 1 auto-reject: Evidence URL is a generic platform '
            f'page, not proof of work: {blocklisted_urls[0][:100]}',
        )
    return None


def rule_cross_user_duplicate_url(submission, evidence_items):
    """Evidence URL already submitted by a different user (copy-paste gaming)."""
    if not evidence_items:
        return None

    urls = [e.url for e in evidence_items if e.url]
    if not urls:
        return None

    from contributions.models import Evidence
    # Skip GitHub repos (can be legitimately shared/forked) and blocklisted URLs
    non_repo_urls = [
        u for u in urls
        if not re.match(r'https?://github\.com/[^/]+/[^/]+/?$', u)
        and not _is_blocklisted_url(u)
    ]
    if not non_repo_urls:
        return None

    # Check if the same URL was submitted by a different user
    other_user_url = (
        Evidence.objects
        .filter(
            url__in=non_repo_urls,
            submitted_contribution__state__in=['pending', 'accepted'],
        )
        .exclude(submitted_contribution__user=submission.user)
        .values_list('url', flat=True)
        .first()
    )
    if other_user_url:
        return (
            'Reject: Duplicate Submission',
            f'Tier 1 auto-reject: Evidence URL was already submitted by '
            f'another user (copy-paste gaming): {other_user_url[:100]}',
        )
    return None


def rule_cross_user_identical_notes(submission, evidence_items):
    """Exact same notes (>20 chars) used by a different user — farming template."""
    notes = (submission.notes or '').strip()
    if len(notes) <= 20:
        return None

    # Skip system-generated notes
    if notes.startswith('Automatic submission'):
        return None

    other_user = (
        SubmittedContribution.objects
        .filter(notes=submission.notes)
        .exclude(user=submission.user)
        .values_list('user__email', flat=True)
        .first()
    )
    if other_user:
        return (
            'Reject: Duplicate Submission',
            f'Tier 1 auto-reject: Identical notes used by another user '
            f'(farming template): {other_user}',
        )
    return None


TIER1_RULES = [
    rule_no_evidence_no_notes,
    rule_no_evidence_short_notes,
    rule_spam_notes,
    rule_duplicate_pending_from_same_user,
    rule_resubmitted_rejected_url,
    rule_same_url_reused_by_same_user,
    rule_blocklisted_evidence_url,
    rule_cross_user_duplicate_url,
    rule_cross_user_identical_notes,
]


# ─── Tier 2 (AI via OpenRouter) ──────────────────────────────────────────────

def build_system_prompt(templates):
    """Build the system prompt for the AI reviewer."""
    template_list = '\n'.join(
        f'  - ID {t.id}: "{t.label}" → {t.text[:120]}...'
        if len(t.text) > 120 else f'  - ID {t.id}: "{t.label}" → {t.text}'
        for t in templates
    )

    return f"""You are an AI reviewer for the GenLayer Testnet Program submission system.

Your job is to evaluate community submissions and propose a review action.

## Context
GenLayer is an AI-native blockchain. The testnet program rewards users for meaningful
contributions like building tools, writing educational content, running validators,
creating documentation, and community building.

## Available Review Templates
{template_list}

## Evaluation Criteria
1. **Evidence quality**: Does the submission include verifiable evidence (GitHub repos,
   blog posts, deployed apps)? Is the evidence real and substantial?
2. **Contribution value**: Does this meaningfully advance the GenLayer ecosystem?
   Simple social media mentions with no depth are low-value.
3. **Originality**: Is this original work or copied/auto-generated content?
4. **Correct categorization**: Did the user select the right contribution type?
   This is critical. Non-technical tweets and social posts submitted as "Educational
   Content", "Documentation", or "Research & Analysis" should be rejected with the
   "Not for Builders: Community Content" template. Builder categories require
   in-depth technical work — community content should be submitted through Discord
   to earn XP.
5. **Duplication**: Has this same work been submitted before by this user?

## Confidence Levels
- HIGH: You are very certain about the action (obvious spam, clearly valuable, etc.)
- MEDIUM: Likely correct but a human should verify
- LOW: Ambiguous, needs human judgment

## Non-Technical Community Content (NOT for Builders)
This is the MOST COMMON mistake. Many users submit simple social media posts or
non-technical overviews under "Educational Content", "Documentation", or "Research
& Analysis" (Builder category). This content is NOT for builders or validators —
it's community engagement that should be submitted through Discord to earn XP
(a dedicated Community section on the platform is coming soon).

**Reject with "Not for Builders: Community Content" template when:**
- A tweet or X post talks about GenLayer in general terms without technical depth
- A post is a "beginner guide" or "how to get started" tweet (not a full tutorial)
- Content is a conceptual overview, awareness post, or promotional thread
- A blog post summarizes what GenLayer is without code examples or technical analysis
- The submission describes GenLayer features at a surface level

**Keep as Educational Content / Documentation / Research when:**
- The content has actual code snippets, smart contract examples, or technical detail
- It's a full blog post or article (not just a tweet) with in-depth technical analysis
- It includes a GitHub repo with real implementation
- The tweet thread is very substantial (10+ tweets) with genuine technical walkthrough

When rejecting for this reason, use the "Not for Builders: Community Content"
template and include the `wrong_type` flag. The staff_reply should tell the user
to submit through Discord to earn XP for community content, and encourage them
to submit technical content for the Builder category.

## Rejection Guidelines (be firm)
- **Tweets/X posts as Educational Content**: A single tweet or short thread about
  GenLayer is NOT "Educational Content", "Documentation", or "Research & Analysis".
  These should be rejected with the "Not for Builders: Community Content" template.
  Do NOT just reject with "Too Superficial" — tell them to submit through Discord
  to earn XP for community content, and that the Builder section needs technical depth.
- **No code, no evidence**: Submissions describing what they *want* to build or *plan* to
  build, without any actual work done, should be rejected.
- **Referral promotion**: Tweets promoting referral codes are never accepted.
- **Generic overviews**: Blog posts or articles that are generic blockchain overviews
  with GenLayer name-dropped are not valuable.
- **AI-generated content**: Content clearly written by AI (generic phrasing, no specific
  details, follows obvious ChatGPT patterns) should be flagged and rejected.

## Acceptance Guidelines (be fair)
- **GitHub repos with real code**: Projects with actual implementation, README, and
  ideally a deployed demo are valuable. Award points based on complexity and quality.
- **Deep technical content**: Blog posts or articles with specific technical details
  about GenLayer's architecture, hands-on tutorials, or detailed comparisons.
- **Tools and infrastructure**: Anything that helps the ecosystem grow — dashboards,
  testing tools, deployment utilities, SDKs.
- **Original research**: Analysis that provides genuine insights, not surface-level
  descriptions.
- Award MINIMAL points (1-2) for borderline acceptable content.
- Award HIGHER points (3-5+) for substantial, high-quality work.

## Important Notes
- Never auto-accept. Acceptances always need human review.
- Users with many prior rejections and zero acceptances are likely spammers.
- Users with prior acceptances are more likely to be legitimate contributors.
- If notes describe a project but evidence is missing, prefer "more_info" over "reject"
  (give them a chance to provide links). But if the user has a history of spam, reject.
- Always include a staff_reply that is helpful and specific to the submission.

Respond ONLY with valid JSON matching the required schema."""


def build_few_shot_examples(contribution_type_id):
    """Build few-shot examples from historical reviewed submissions of the same type."""
    examples = []

    # Get accepted examples for this type
    accepted = (
        SubmittedContribution.objects
        .filter(
            contribution_type_id=contribution_type_id,
            state='accepted',
        )
        .select_related('contribution_type', 'user', 'converted_contribution')
        .prefetch_related('evidence_items')
        .order_by('-reviewed_at')[:5]
    )

    for sub in accepted:
        evidence_urls = [e.url for e in sub.evidence_items.all() if e.url]
        points = (
            sub.converted_contribution.points
            if sub.converted_contribution else None
        )
        examples.append({
            'role': 'accepted',
            'notes': (sub.notes or '')[:300],
            'evidence_urls': evidence_urls[:3],
            'staff_reply': (sub.staff_reply or '')[:200],
            'points': points,
        })

    # Get rejected examples for this type
    rejected = (
        SubmittedContribution.objects
        .filter(
            contribution_type_id=contribution_type_id,
            state='rejected',
        )
        .select_related('contribution_type')
        .prefetch_related('evidence_items')
        .order_by('-reviewed_at')[:5]
    )

    for sub in rejected:
        evidence_urls = [e.url for e in sub.evidence_items.all() if e.url]
        examples.append({
            'role': 'rejected',
            'notes': (sub.notes or '')[:300],
            'evidence_urls': evidence_urls[:3],
            'staff_reply': (sub.staff_reply or '')[:200],
        })

    return examples


def build_user_message(submission, evidence_items, user_history):
    """Build the user message for a single submission."""
    evidence_data = []
    for e in evidence_items:
        item = {}
        if e.url:
            item['url'] = e.url
        if e.description:
            item['description'] = e.description[:200]
        if item:
            evidence_data.append(item)

    # Build few-shot examples for this contribution type
    examples = build_few_shot_examples(submission.contribution_type_id)
    examples_str = ''
    if examples:
        examples_str = (
            f'\n\n## Historical Examples for '
            f'"{submission.contribution_type.name}"\n'
        )
        for i, ex in enumerate(examples, 1):
            examples_str += f'\nExample {i} ({ex["role"]}):\n'
            examples_str += f'  Notes: {ex["notes"][:200]}\n'
            examples_str += (
                f'  Evidence: {", ".join(ex.get("evidence_urls", []))}\n'
            )
            if ex.get('staff_reply'):
                examples_str += f'  Staff reply: {ex["staff_reply"][:150]}\n'
            if ex.get('points'):
                examples_str += f'  Points awarded: {ex["points"]}\n'

    category_name = (
        submission.contribution_type.category.name
        if submission.contribution_type.category else 'N/A'
    )

    return f"""## Submission to Review
- **Type**: {submission.contribution_type.name} (Category: {category_name})
- **Notes**: {(submission.notes or '(empty)')[:500]}
- **Evidence**: {json.dumps(evidence_data) if evidence_data else '(none)'}
- **Submitted**: {submission.created_at.strftime('%Y-%m-%d')}

## User History
- Accepted submissions: {user_history['accepted']}
- Rejected submissions: {user_history['rejected']}
- Pending submissions: {user_history['pending']}
- Rejection rate: {user_history['rejection_rate']}%{' ⚠️ HIGH REJECTION RATE' if user_history['rejection_rate'] >= 80 and user_history['total_reviewed'] >= 3 else ''}
{'- Spam signals: ' + '; '.join(user_history.get('spam_signals', [])) if user_history.get('spam_signals') else ''}

## Contribution Type Constraints
- Min points: {submission.contribution_type.min_points}
- Max points: {submission.contribution_type.max_points}
{examples_str}

Please evaluate this submission and respond with JSON:
{{
    "action": "accept" | "reject" | "more_info",
    "template_id": <int>,
    "staff_reply": "<personalized reply based on template, or template text if no personalization needed>",
    "points": <int or null>,
    "confidence": "high" | "medium" | "low",
    "reasoning": "<internal reasoning for CRM note>",
    "flags": ["<optional flags: ai_generated, plagiarism, low_effort, wrong_type, duplicate>"]
}}"""


def call_openrouter(system_prompt, user_message, model=None):
    """Call the OpenRouter API and return (parsed_json, usage_dict)."""
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        raise ValueError(
            'OPENROUTER_API_KEY environment variable is required for Tier 2. '
            'Set it in your .env file.'
        )

    model = model or OPENROUTER_MODEL

    response = http_requests.post(
        OPENROUTER_API_URL,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://points.genlayer.foundation',
            'X-Title': 'GenLayer Submission Review',
        },
        json={
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message},
            ],
            'max_tokens': 1024,
            'temperature': 0.1,
        },
        timeout=120,
    )

    if response.status_code != 200:
        raise ValueError(
            f'OpenRouter API error {response.status_code}: {response.text[:500]}'
        )

    data = response.json()

    # Extract usage
    usage = data.get('usage', {})
    usage_info = {
        'input_tokens': usage.get('prompt_tokens', 0),
        'output_tokens': usage.get('completion_tokens', 0),
        'model': model,
    }

    # Calculate cost
    pricing = MODEL_PRICING.get(model, {'input': 0, 'output': 0})
    usage_info['cost_usd'] = (
        usage_info['input_tokens'] * pricing['input'] / 1_000_000
        + usage_info['output_tokens'] * pricing['output'] / 1_000_000
    )

    # Parse response content
    text = data['choices'][0]['message']['content'].strip()
    # Handle markdown code blocks
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()

    # Try to extract JSON from the response if direct parse fails
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            raise

    return result, usage_info


def classify_with_ai(submission, evidence_items, user_history, templates,
                     model=None, max_retries=2):
    """Classify a submission using the AI via OpenRouter."""
    system_prompt = build_system_prompt(templates)
    user_message = build_user_message(submission, evidence_items, user_history)

    last_error = None
    total_usage = {'input_tokens': 0, 'output_tokens': 0, 'cost_usd': 0.0}
    for attempt in range(max_retries + 1):
        try:
            result, usage = call_openrouter(
                system_prompt, user_message, model=model,
            )
            # Accumulate cost across retries
            total_usage['input_tokens'] += usage.get('input_tokens', 0)
            total_usage['output_tokens'] += usage.get('output_tokens', 0)
            total_usage['cost_usd'] += usage.get('cost_usd', 0.0)
            total_usage['model'] = usage.get('model')

            # Validate required fields
            required = ['action', 'template_id', 'confidence', 'reasoning']
            for field in required:
                if field not in result:
                    raise ValueError(
                        f'AI response missing required field: {field}'
                    )

            if result['action'] not in ('accept', 'reject', 'more_info'):
                raise ValueError(f'Invalid action: {result["action"]}')

            if result['confidence'] not in ('high', 'medium', 'low'):
                raise ValueError(
                    f'Invalid confidence: {result["confidence"]}'
                )

            result['_usage'] = total_usage
            return result
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(1)  # Brief pause before retry
                continue

    raise last_error


# ─── Command ─────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Review pending submissions using deterministic rules and AI'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would happen without making changes',
        )
        parser.add_argument(
            '--tier1-only',
            action='store_true',
            help='Only run Tier 1 deterministic rules',
        )
        parser.add_argument(
            '--tier2-only',
            action='store_true',
            help='Only run Tier 2 AI classification (skip Tier 1)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=0,
            help='Max submissions to process (0 = all)',
        )
        parser.add_argument(
            '--type',
            type=str,
            help='Only process submissions of this contribution type name',
        )
        parser.add_argument(
            '--submission-id',
            type=str,
            help='Process a specific submission by UUID',
        )
        parser.add_argument(
            '--model',
            type=str,
            default=None,
            help=(
                'Override AI model '
                '(e.g., anthropic/claude-sonnet-4-20250514)'
            ),
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        tier1_only = options['tier1_only']
        tier2_only = options['tier2_only']
        batch_size = options['batch_size']
        model_override = options.get('model')

        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE ==='))

        # Ensure AI steward exists
        ai_user = self.ensure_ai_steward()

        # Load templates
        templates = {t.label: t for t in ReviewTemplate.objects.all()}
        if not templates:
            self.stdout.write(self.style.ERROR(
                'No review templates found. Please create them first.'
            ))
            return

        # Build queryset
        qs = SubmittedContribution.objects.filter(
            state__in=['pending', 'more_info_needed'],
        ).select_related(
            'contribution_type',
            'contribution_type__category',
            'user',
        ).prefetch_related('evidence_items')

        if options['submission_id']:
            qs = qs.filter(id=options['submission_id'])
        if options['type']:
            qs = qs.filter(contribution_type__name=options['type'])

        # Don't re-process submissions already reviewed/proposed by AI
        qs = qs.filter(
            Q(proposed_by__isnull=True) | ~Q(proposed_by=ai_user),
        ).exclude(reviewed_by=ai_user)

        if batch_size > 0:
            qs = qs[:batch_size]

        submissions = list(qs)
        self.stdout.write(f'Found {len(submissions)} submissions to process')

        # Stats & cost tracking
        stats = defaultdict(int)
        total_cost = 0.0
        total_input_tokens = 0
        total_output_tokens = 0

        for i, submission in enumerate(submissions, 1):
            evidence_items = list(submission.evidence_items.all())
            self.stdout.write(
                f'\n[{i}/{len(submissions)}] {submission.id} '
                f'| {submission.contribution_type.name} '
                f'| evidence: {len(evidence_items)} '
                f'| notes: {len((submission.notes or ""))}chars'
            )

            # ── Tier 1: Deterministic rules ──
            if not tier2_only:
                tier1_result = self.run_tier1(
                    submission, evidence_items, templates,
                )
                if tier1_result:
                    template, crm_reason = tier1_result
                    stats['tier1_reject'] += 1
                    self.stdout.write(self.style.WARNING(
                        f'  -> Tier 1 REJECT: {template.label}'
                    ))
                    if not dry_run:
                        self.apply_direct_reject(
                            submission, ai_user, template, crm_reason,
                        )
                    continue

            # ── Tier 2: AI classification ──
            if not tier1_only:
                tier2_result = self.run_tier2(
                    submission, evidence_items, ai_user, templates,
                    dry_run, model_override,
                )
                if tier2_result:
                    action = tier2_result['action']
                    confidence = tier2_result['confidence']
                    stats[f'tier2_{action}_{confidence}'] += 1

                    usage = tier2_result.get('_usage', {})
                    total_cost += usage.get('cost_usd', 0)
                    total_input_tokens += usage.get('input_tokens', 0)
                    total_output_tokens += usage.get('output_tokens', 0)

            if tier1_only:
                stats['tier1_pass'] += 1

        # ── Auto-ban check ──
        banned_count = self.check_auto_bans(ai_user, dry_run)
        stats['auto_banned'] = banned_count

        # ── Print summary ──
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        for key, count in sorted(stats.items()):
            if count > 0:
                self.stdout.write(f'  {key}: {count}')

        if total_cost > 0:
            self.stdout.write(f'\n  API Usage:')
            self.stdout.write(f'    Input tokens:  {total_input_tokens:,}')
            self.stdout.write(f'    Output tokens: {total_output_tokens:,}')
            self.stdout.write(f'    Total cost:    ${total_cost:.4f}')

        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\nDry run complete. No changes made.'
            ))

    def ensure_ai_steward(self):
        """Get or create the AI steward user."""
        user, created = User.objects.get_or_create(
            email=AI_STEWARD_EMAIL,
            defaults={
                'name': AI_STEWARD_NAME,
                'visible': False,
            },
        )
        if created:
            user.set_unusable_password()
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f'Created AI steward user: {user.email}'
            ))

        # Ensure steward profile
        steward, created = Steward.objects.get_or_create(user=user)
        if created:
            self.stdout.write(self.style.SUCCESS(
                f'Created steward profile for {user.email}'
            ))

        # Ensure permissions for all contribution types and all actions
        actions = ['propose', 'accept', 'reject', 'request_more_info']
        for ct in ContributionType.objects.all():
            for action in actions:
                StewardPermission.objects.get_or_create(
                    steward=steward,
                    contribution_type=ct,
                    action=action,
                )

        return user

    def check_auto_bans(self, ai_user, dry_run):
        """
        Auto-ban users who meet the threshold:
        5+ total rejections AND 0 acceptances (100% rejection rate).
        Only bans users who aren't already banned.
        """
        from django.db.models import Count, Q

        # Find users with 5+ rejections and 0 acceptances, not already banned
        candidates = (
            User.objects
            .filter(is_banned=False)
            .exclude(email=AI_STEWARD_EMAIL)
            .annotate(
                total_rejected=Count(
                    'submitted_contributions',
                    filter=Q(submitted_contributions__state='rejected'),
                ),
                total_accepted=Count(
                    'submitted_contributions',
                    filter=Q(submitted_contributions__state='accepted'),
                ),
            )
            .filter(total_rejected__gte=5, total_accepted=0)
        )

        banned_count = 0
        for user in candidates:
            self.stdout.write(self.style.WARNING(
                f'  AUTO-BAN: {user.email} '
                f'({user.total_rejected} rejections, 0 acceptances)'
            ))
            if not dry_run:
                user.is_banned = True
                user.ban_reason = (
                    f'Auto-banned: {user.total_rejected} consecutive '
                    f'rejections with no accepted contributions.'
                )
                user.banned_at = timezone.now()
                user.banned_by = ai_user
                user.save()
            banned_count += 1

        if banned_count > 0:
            self.stdout.write(self.style.WARNING(
                f'\n  {banned_count} user(s) {"would be" if dry_run else ""} '
                f'auto-banned.'
            ))
        return banned_count

    def run_tier1(self, submission, evidence_items, templates):
        """Run Tier 1 deterministic rules. Returns (template, crm_reason) or None."""
        for rule_fn in TIER1_RULES:
            result = rule_fn(submission, evidence_items)
            if result:
                template_label, crm_reason = result
                template = templates.get(template_label)
                if template is None:
                    self.stdout.write(self.style.ERROR(
                        f'  Template not found: {template_label}'
                    ))
                    continue
                return template, crm_reason
        return None

    def apply_direct_reject(self, submission, ai_user, template, crm_reason):
        """Apply a direct rejection (100% confidence Tier 1)."""
        submission.state = 'rejected'
        submission.staff_reply = template.text
        submission.reviewed_by = ai_user
        submission.reviewed_at = timezone.now()
        # Clear any existing proposal fields
        submission.proposed_action = None
        submission.proposed_points = None
        submission.proposed_contribution_type = None
        submission.proposed_user = None
        submission.proposed_staff_reply = ''
        submission.proposed_create_highlight = False
        submission.proposed_highlight_title = ''
        submission.proposed_highlight_description = ''
        submission.proposed_by = None
        submission.proposed_at = None
        submission.save()

        SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=ai_user,
            message=crm_reason,
            is_proposal=False,
            data={
                'action': 'reject',
                'points': None,
                'staff_reply': template.text,
                'template_id': template.id,
                'confidence': 'high',
                'flags': [],
                'reasoning': crm_reason,
            },
        )

    def _compute_spam_signals(self, submission, evidence_items):
        """Compute additional spam signals for AI context."""
        signals = []
        from contributions.models import Evidence

        urls = [e.url for e in evidence_items if e.url]

        # Daily submission velocity
        from django.db.models.functions import TruncDate
        from django.db.models import Count
        if submission.created_at:
            same_day = (
                SubmittedContribution.objects
                .filter(
                    user=submission.user,
                    created_at__date=submission.created_at.date(),
                )
                .count()
            )
            if same_day >= 5:
                signals.append(
                    f'HIGH VELOCITY: {same_day} submissions on same day'
                )

        # Check for "airdrop" in user email
        email = submission.user.email.lower()
        if 'airdrop' in email:
            signals.append('SUSPICIOUS EMAIL: contains "airdrop"')

        # Check total pending count (shotgun submitter)
        pending_count = (
            SubmittedContribution.objects
            .filter(user=submission.user, state='pending')
            .count()
        )
        if pending_count >= 8:
            distinct_types = (
                SubmittedContribution.objects
                .filter(user=submission.user, state='pending')
                .values('contribution_type')
                .distinct()
                .count()
            )
            signals.append(
                f'BULK SUBMITTER: {pending_count} pending across '
                f'{distinct_types} types'
            )

        return signals

    def run_tier2(self, submission, evidence_items, ai_user, templates,
                  dry_run, model_override=None):
        """Run Tier 2 AI classification. Returns the AI result dict or None."""
        # Get user history
        accepted = SubmittedContribution.objects.filter(
            user=submission.user, state='accepted',
        ).count()
        rejected = SubmittedContribution.objects.filter(
            user=submission.user, state='rejected',
        ).count()
        pending = SubmittedContribution.objects.filter(
            user=submission.user, state='pending',
        ).count()
        total_reviewed = accepted + rejected
        rejection_rate = (
            round(rejected * 100 / total_reviewed) if total_reviewed > 0
            else 0
        )
        user_history = {
            'accepted': accepted,
            'rejected': rejected,
            'pending': pending,
            'total_reviewed': total_reviewed,
            'rejection_rate': rejection_rate,
            'spam_signals': self._compute_spam_signals(
                submission, evidence_items,
            ),
        }

        try:
            template_objects = list(ReviewTemplate.objects.all())
            result = classify_with_ai(
                submission, evidence_items, user_history, template_objects,
                model=model_override,
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  -> AI error: {e}'))
            return None

        action = result['action']
        confidence = result['confidence']
        reasoning = result.get('reasoning', '')
        flags = result.get('flags', [])
        points = result.get('points')
        staff_reply = result.get('staff_reply', '')
        usage = result.get('_usage', {})

        flag_str = f' [{", ".join(flags)}]' if flags else ''
        cost_str = f' (${usage.get("cost_usd", 0):.4f})' if usage else ''
        self.stdout.write(
            f'  -> AI: {action} (confidence: {confidence}){flag_str}{cost_str}'
        )
        self.stdout.write(f'     Reasoning: {reasoning[:150]}')

        if dry_run:
            return result

        # All Tier 2 results are proposals for human review
        # (only Tier 1 deterministic rules auto-reject)
        submission.proposed_action = action
        submission.proposed_points = points if action == 'accept' else None
        submission.proposed_staff_reply = staff_reply
        submission.proposed_by = ai_user
        submission.proposed_at = timezone.now()
        submission.save()

        crm_msg = (
            f'AI proposal ({confidence} confidence): {action}\n'
            f'Reasoning: {reasoning}\n'
            f'Flags: {", ".join(flags) if flags else "none"}'
        )
        SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=ai_user,
            message=crm_msg,
            is_proposal=True,
            data={
                'action': action,
                'points': points,
                'staff_reply': staff_reply,
                'template_id': result.get('template_id'),
                'confidence': confidence,
                'flags': flags,
                'reasoning': reasoning,
            },
        )

        return result
