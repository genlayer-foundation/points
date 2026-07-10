"""
Deterministic submission review management command.

Processes pending submissions through three Tier 1 rules for auto-rejection:
  1. No evidence URL
  2. Blocklisted evidence URL
  3. Duplicate evidence URL (any user)

Usage:
    # Dry run - see what would happen without making changes
    python manage.py review_submissions --dry-run

    # Full run with batch size
    python manage.py review_submissions --batch-size 50

    # Filter by contribution type
    python manage.py review_submissions --type "Educational Content"

    # Process a specific submission
    python manage.py review_submissions --submission-id <uuid>
"""

import logging
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from contributions.ai_attribution import AI_STEWARD_EMAIL, get_ai_steward
from contributions.models import (
    BlocklistedURL,
    ContributionType,
    Evidence,
    SubmissionNote,
    SubmissionStateTransition,
    SubmittedContribution,
)
from stewards.models import ReviewTemplate, Steward, StewardPermission
from users.models import User

logger = logging.getLogger(__name__)

MISSING_TEMPLATE = object()


# ─── URL Helpers ─────────────────────────────────────────────────────────────

from contributions.url_utils import normalize_url as _normalize_url_full


def _normalize_url(url):
    """Normalize a URL for comparison.

    Uses the shared normalize_url utility but falls back to basic stripping
    for backward compatibility with how this command builds its lookup dicts.
    """
    return _normalize_url_full(url)


def _normalize_url_for_blocklist(url):
    """Normalize a URL for blocklist comparison -- strips ALL query params.

    The blocklist compares URL prefixes, so query params must be removed
    entirely to prevent bypass via ?foo=1.
    """
    from urllib.parse import urlparse
    if not url:
        return ''
    parsed = urlparse(url)
    scheme = (parsed.scheme or 'https').lower()
    host = (parsed.netloc or '').lower()
    path = parsed.path.rstrip('/')
    return f"{scheme}://{host}{path}"


def _load_blocklist():
    """Load blocklisted URL prefixes from the database."""
    return list(
        BlocklistedURL.objects.values_list('url_prefix', flat=True)
    )


def _is_blocklisted_url(url, blocklist):
    """Check if URL matches a blocklisted platform prefix."""
    normalized = _normalize_url_for_blocklist(url)
    for prefix in blocklist:
        if normalized == prefix or normalized.startswith(prefix + '/'):
            return True
    return False


# ─── Tier 1 Rules ────────────────────────────────────────────────────────────
# Each rule returns (template_label, crm_reason) or None.
# Evaluated in order: no-evidence → blocklisted → duplicate.


def rule_no_evidence_url(submission, evidence_items):
    """Submission has no evidence items with a non-empty URL."""
    if any(e.url for e in evidence_items):
        return None
    return (
        'Reject: No Evidence',
        'Tier 1 auto-reject: No evidence URL provided.',
    )


def rule_blocklisted_url(submission, evidence_items, blocklist):
    """All evidence URLs are generic platform pages, not actual work."""
    urls = [e.url for e in evidence_items if e.url]
    if not urls:
        return None  # Handled by rule_no_evidence_url
    if all(_is_blocklisted_url(u, blocklist) for u in urls):
        return (
            'Reject: Invalid Evidence URL',
            f'Tier 1 auto-reject: All evidence URLs are generic platform '
            f'pages: {urls[0][:100]}',
        )
    return None


def rule_duplicate_evidence_url(submission, evidence_items,
                                url_to_sub_ids, accepted_urls,
                                skip_pending=False,
                                submitted_created_at=None):
    """Reject only when ALL evidence URLs are duplicates.

    A submission with multiple evidence URLs is only rejected if every single
    URL already exists elsewhere. If at least one URL is unique, the submission
    passes this rule.

    URLs are normalized (query params, fragments, trailing slashes stripped)
    before comparison to prevent cosmetic variants from bypassing the check.

    Args:
        Pending submission duplicates only count when the duplicate is older,
        unless skip_pending is set for a targeted command run.
        Accepted contribution duplicates always count.
    """
    urls_with_evidence = [(e, _normalize_url(e.url))
                          for e in evidence_items if e.url]
    if not urls_with_evidence:
        return None

    # Check each URL; collect reasons but only reject if ALL are duplicates.
    duplicate_reasons = []
    for evidence, normalized in urls_with_evidence:
        reason = _check_single_url_duplicate(
            submission, evidence, normalized,
            url_to_sub_ids, accepted_urls,
            skip_pending, submitted_created_at,
        )
        if reason is None:
            # At least one URL is unique — submission passes.
            return None
        duplicate_reasons.append(reason)

    # All URLs are duplicates — use the first reason for the rejection message.
    return duplicate_reasons[0]


def _check_single_url_duplicate(submission, evidence, normalized,
                                url_to_sub_ids, accepted_urls,
                                skip_pending, submitted_created_at):
    """Check whether a single normalized URL is a duplicate.

    Returns (template_label, crm_reason) if duplicate, or None if unique.
    """
    # URL types flagged as duplicate-allowed are exempt. Fall back to
    # pattern detection when url_type is missing (legacy rows or evidence
    # copied via bulk_create paths that didn't populate the FK).
    if evidence.url_type_id and evidence.url_type and evidence.url_type.allow_duplicate:
        return None
    if not evidence.url_type_id and evidence.url:
        from contributions.url_utils import detect_url_type
        detected = detect_url_type(evidence.url)
        if detected and detected.allow_duplicate:
            return None
    # Check converted/accepted contributions (always deterministic)
    if normalized in accepted_urls:
        return (
            'Reject: Duplicate Submission',
            f'Tier 1 auto-reject: Evidence URL already exists in an '
            f'accepted contribution: {evidence.url[:100]}',
        )
    # Check pending/accepted submitted contributions (exclude self)
    others = (url_to_sub_ids.get(normalized) or set()) - {submission.id}
    if skip_pending and others:
        pending_states = {'pending', 'more_info_needed'}
        others = set(
            SubmittedContribution.objects
            .filter(id__in=others)
            .exclude(state__in=pending_states)
            .values_list('id', flat=True)
        )
    if not others:
        return None

    submission_key = (submission.created_at, str(submission.id))
    created_at_lookup = submitted_created_at or {}
    missing_created_at_ids = [
        other_id for other_id in others
        if other_id not in created_at_lookup
    ]
    if missing_created_at_ids:
        created_at_lookup = {
            **created_at_lookup,
            **dict(
                SubmittedContribution.objects
                .filter(id__in=missing_created_at_ids)
                .values_list('id', 'created_at')
            ),
        }
    if any(
        (
            created_at_lookup.get(other_id, submission.created_at),
            str(other_id),
        ) < submission_key
        for other_id in others
    ):
        return (
            'Reject: Duplicate Submission',
            f'Tier 1 auto-reject: Evidence URL already exists in an older '
            f'submission: {evidence.url[:100]}',
        )
    return None


# ─── Command ─────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Review pending submissions using deterministic rules'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would happen without making changes',
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

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE ==='))

        ai_user = self._ensure_ai_steward()

        templates = {t.label: t for t in ReviewTemplate.objects.all()}
        if not templates:
            self.stdout.write(self.style.ERROR(
                'No review templates found. Please create them first.'
            ))
            return

        # Build queryset
        qs = (
            SubmittedContribution.objects
            .filter(state__in=['pending', 'more_info_needed'])
            .select_related(
                'contribution_type',
                'contribution_type__category',
                'user',
            )
            .prefetch_related('evidence_items')
        )

        if options['submission_id']:
            qs = qs.filter(id=options['submission_id'])
        if options['type']:
            qs = qs.filter(contribution_type__name=options['type'])

        # Skip submissions already reviewed by AI steward or carrying an
        # active proposal, since Tier 1 should not overwrite proposal state.
        # Also skip appealed submissions — those are reserved for human
        # steward reconsideration.
        qs = qs.exclude(reviewed_by=ai_user).filter(
            gate_reviewed=False,
            proposed_action__isnull=True,
            has_appeal=False,
        )

        # Process newest first so that when duplicates share a URL,
        # the newer copy is rejected and the oldest original survives.
        qs = qs.order_by('-created_at')

        if batch_size > 0:
            qs = qs[:batch_size]

        submissions = list(qs)
        self.stdout.write(f'Found {len(submissions)} submissions to process')

        # Pre-load all evidence URLs for O(1) duplicate checking
        url_to_sub_ids, accepted_urls, submitted_created_at = (
            self._build_url_lookup()
        )

        # Load blocklisted URL prefixes from database
        blocklist = _load_blocklist()
        self.stdout.write(f'Loaded {len(blocklist)} blocklisted URL prefixes')

        # When targeting a single submission, duplicate checks still run, but
        # only older submitted duplicates count so the outcome is deterministic.
        skip_pending_duplicates = bool(options['submission_id'])

        stats = defaultdict(int)

        for i, submission in enumerate(submissions, 1):
            evidence_items = list(submission.evidence_items.all())
            self.stdout.write(
                f'\n[{i}/{len(submissions)}] {submission.id} '
                f'| {submission.contribution_type.name} '
                f'| evidence: {len(evidence_items)} '
                f'| notes: {len((submission.notes or ""))}chars'
            )

            result = self._run_tier1(
                submission, evidence_items, templates,
                url_to_sub_ids, accepted_urls, submitted_created_at, blocklist,
                skip_pending_duplicates=skip_pending_duplicates,
            )
            if result is MISSING_TEMPLATE:
                stats['errors'] += 1
                continue
            elif result:
                template, crm_reason = result
                stats['rejected'] += 1
                self.stdout.write(self.style.WARNING(
                    f'  -> REJECT: {template.label}'
                ))
                if not dry_run:
                    self._apply_reject(
                        submission, ai_user, template, crm_reason,
                    )
                # Remove rejected submission from URL lookup so later
                # submissions sharing the same URL aren't falsely rejected
                self._remove_from_url_lookup(
                    submission, evidence_items, url_to_sub_ids,
                )
            else:
                stats['passed'] += 1
                if not dry_run:
                    self._mark_gate_reviewed(submission)

        # Auto-ban check
        banned_count = self._check_auto_bans(ai_user, dry_run)
        stats['auto_banned'] = banned_count

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        for key, count in sorted(stats.items()):
            if count > 0:
                self.stdout.write(f'  {key}: {count}')

        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\nDry run complete. No changes made.'
            ))

    def _build_url_lookup(self):
        """Pre-load all evidence URLs for O(1) duplicate checking.

        URLs are normalized (query params, fragments, trailing slashes
        stripped) so that cosmetic variants map to the same key.

        Returns:
            url_to_sub_ids: dict mapping normalized URL → set of submission IDs
            accepted_urls: set of normalized URLs from accepted contributions
            submitted_created_at: dict mapping submission ID → created_at
        """
        # URLs from pending/accepted submitted contributions.
        # Evidence whose url_type allows duplicates is excluded so those
        # URLs never participate in duplicate detection.
        from contributions.url_utils import detect_url_type

        submitted = (
            Evidence.objects
            .filter(
                submitted_contribution__state__in=[
                    'pending', 'accepted', 'more_info_needed',
                ],
                url__gt='',
            )
            .values_list(
                'url',
                'submitted_contribution_id',
                'submitted_contribution__created_at',
                'url_type__allow_duplicate',
            )
        )
        url_to_sub_ids = defaultdict(set)
        submitted_created_at = {}
        for url, sub_id, created_at, allow_duplicate in submitted:
            if allow_duplicate:
                continue
            if allow_duplicate is None:
                detected = detect_url_type(url)
                if detected and detected.allow_duplicate:
                    continue
            url_to_sub_ids[_normalize_url(url)].add(sub_id)
            submitted_created_at.setdefault(sub_id, created_at)

        # URLs from converted/accepted contributions
        accepted_urls = set()
        for url, allow_duplicate in (
            Evidence.objects
            .filter(contribution__isnull=False, url__gt='')
            .values_list('url', 'url_type__allow_duplicate')
        ):
            if allow_duplicate:
                continue
            if allow_duplicate is None:
                detected = detect_url_type(url)
                if detected and detected.allow_duplicate:
                    continue
            accepted_urls.add(_normalize_url(url))

        return url_to_sub_ids, accepted_urls, submitted_created_at

    def _remove_from_url_lookup(self, submission, evidence_items,
                                url_to_sub_ids):
        """Remove a rejected submission from the URL lookup so later
        submissions sharing the same URL aren't falsely rejected."""
        for e in evidence_items:
            if e.url:
                normalized = _normalize_url(e.url)
                if normalized in url_to_sub_ids:
                    url_to_sub_ids[normalized].discard(submission.id)

    def _run_tier1(self, submission, evidence_items, templates,
                   url_to_sub_ids, accepted_urls, submitted_created_at,
                   blocklist,
                   skip_pending_duplicates=False):
        """Run Tier 1 rules in order. Returns result tuple, sentinel, or None."""
        # Rule 1: No evidence URL
        result = rule_no_evidence_url(submission, evidence_items)
        if result:
            return self._resolve_template(result, templates)

        # Rule 2: Blocklisted URL
        result = rule_blocklisted_url(submission, evidence_items, blocklist)
        if result:
            return self._resolve_template(result, templates)

        # Rule 3: Duplicate evidence URL
        # For --submission-id runs, only check against accepted contributions
        # (deterministic) and skip the pending lookup (order-dependent).
        result = rule_duplicate_evidence_url(
            submission, evidence_items, url_to_sub_ids, accepted_urls,
            skip_pending=skip_pending_duplicates,
            submitted_created_at=submitted_created_at,
        )
        if result:
            return self._resolve_template(result, templates)

        return None

    def _resolve_template(self, rule_result, templates):
        """Look up the template for a rule result."""
        template_label, crm_reason = rule_result
        template = templates.get(template_label)
        if template is None:
            self.stdout.write(self.style.ERROR(
                f'  Template not found: {template_label}'
            ))
            return MISSING_TEMPLATE
        return template, crm_reason

    @transaction.atomic
    def _apply_reject(self, submission, ai_user, template, crm_reason):
        """Apply a direct rejection."""
        previous_state = submission.state
        submission.state = 'rejected'
        submission.staff_reply = template.text
        submission.reviewed_by = ai_user
        submission.reviewed_at = timezone.now()
        submission.gate_reviewed = True
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
        submission.proposed_confidence = None
        submission.proposed_template = None
        submission.proposal_review_status = None
        submission.proposal_review_feedback = ''
        submission.proposal_questioned_by = None
        submission.proposal_questioned_at = None
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

        SubmissionStateTransition.record(
            submission,
            SubmissionStateTransition.EVENT_GATE_REJECT,
            from_state=previous_state,
            actor=ai_user,
        )

    def _mark_gate_reviewed(self, submission):
        """Record that Tier 1 evaluated this submission and found no reject."""
        if submission.gate_reviewed:
            return
        submission.gate_reviewed = True
        submission.save(update_fields=['gate_reviewed', 'updated_at'])

    def _ensure_ai_steward(self):
        """Get or create the AI steward user with full steward permissions."""
        user = get_ai_steward()

        steward, created = Steward.objects.get_or_create(user=user)
        if created:
            self.stdout.write(self.style.SUCCESS(
                f'Created steward profile for {user.email}'
            ))

        actions = ['propose', 'accept', 'reject', 'request_more_info']
        for ct in ContributionType.objects.all():
            for action in actions:
                StewardPermission.objects.get_or_create(
                    steward=steward,
                    contribution_type=ct,
                    action=action,
                )

        return user

    def _check_auto_bans(self, ai_user, dry_run):
        """Auto-ban users with 5+ rejections and 0 acceptances."""
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
