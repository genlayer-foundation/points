"""
Find duplicate X/Twitter post submissions.

Compares evidence URLs across both submissions (SubmittedContribution) and
accepted contributions (Contribution) to find cases where the same X post
was submitted by multiple users. The oldest record is considered the
legitimate "post owner".

Uses raw values queries to avoid loading full User model (which may have
columns not yet present in the target database).

Usage:
    python manage.py find_duplicate_x_posts
    python manage.py find_duplicate_x_posts --state pending
    python manage.py find_duplicate_x_posts --csv
"""

import re
from collections import defaultdict

from django.core.management.base import BaseCommand

from contributions.models import Evidence, SubmittedContribution


# Match x.com and twitter.com status URLs
X_URL_PATTERN = re.compile(
    r'https?://(?:www\.)?(?:twitter\.com|x\.com)/([^/]+)/status/(\d+)',
    re.IGNORECASE,
)


def normalize_x_url(url):
    """Extract canonical (username, status_id) from an X/Twitter URL."""
    match = X_URL_PATTERN.search(url)
    if not match:
        return None
    username = match.group(1).lower()
    status_id = match.group(2)
    return (username, status_id)


class EvidenceRecord:
    """Lightweight record — no ORM model instances."""

    def __init__(self, url, user_id, user_display, created_at, state, record_id, source):
        self.url = url
        self.user_id = user_id
        self.user_display = user_display
        self.created_at = created_at
        self.state = state
        self.record_id = record_id
        self.source = source  # 'submission' or 'contribution'


class Command(BaseCommand):
    help = 'Find duplicate X/Twitter post submissions across users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--state',
            type=str,
            default=None,
            help='Filter by submission state (pending, accepted, rejected). Default: all.',
        )
        parser.add_argument(
            '--csv',
            action='store_true',
            help='Output in CSV format.',
        )

    def handle(self, *args, **options):
        state_filter = options['state']
        csv_output = options['csv']

        posts = defaultdict(list)

        # Build set of contribution IDs that are converted from submissions,
        # so we can skip their evidence (it's a copy of the submission evidence).
        converted_contrib_ids = set(
            SubmittedContribution.objects
            .filter(converted_contribution__isnull=False)
            .values_list('converted_contribution_id', flat=True)
        )

        # 1. Evidence from SubmittedContributions — use values() to avoid loading User model
        sub_evidence_qs = Evidence.objects.filter(
            submitted_contribution__isnull=False,
        ).values(
            'url',
            'submitted_contribution__id',
            'submitted_contribution__user_id',
            'submitted_contribution__user__name',
            'submitted_contribution__user__email',
            'submitted_contribution__user__address',
            'submitted_contribution__state',
            'submitted_contribution__created_at',
        )
        if state_filter:
            sub_evidence_qs = sub_evidence_qs.filter(
                submitted_contribution__state=state_filter,
            )

        for row in sub_evidence_qs:
            url = row['url']
            if not url:
                continue
            key = normalize_x_url(url)
            if key is None:
                continue
            name = row['submitted_contribution__user__name']
            email = row['submitted_contribution__user__email']
            address = row['submitted_contribution__user__address']
            user_display = name or email or (str(address)[:16] if address else '?')
            posts[key].append(EvidenceRecord(
                url=url,
                user_id=row['submitted_contribution__user_id'],
                user_display=user_display,
                created_at=row['submitted_contribution__created_at'],
                state=row['submitted_contribution__state'],
                record_id=str(row['submitted_contribution__id']),
                source='submission',
            ))

        # 2. Evidence from Contributions that were NOT converted from a submission
        if not state_filter or state_filter == 'accepted':
            contrib_evidence_qs = Evidence.objects.filter(
                contribution__isnull=False,
            ).exclude(
                contribution_id__in=converted_contrib_ids,
            ).values(
                'url',
                'contribution__id',
                'contribution__user_id',
                'contribution__user__name',
                'contribution__user__email',
                'contribution__user__address',
                'contribution__created_at',
            )

            for row in contrib_evidence_qs:
                url = row['url']
                if not url:
                    continue
                key = normalize_x_url(url)
                if key is None:
                    continue
                name = row['contribution__user__name']
                email = row['contribution__user__email']
                address = row['contribution__user__address']
                user_display = name or email or (str(address)[:16] if address else '?')
                posts[key].append(EvidenceRecord(
                    url=url,
                    user_id=row['contribution__user_id'],
                    user_display=user_display,
                    created_at=row['contribution__created_at'],
                    state='contribution',
                    record_id=str(row['contribution__id']),
                    source='contribution',
                ))

        # Deduplicate by (source, record_id) within each group
        for key in list(posts.keys()):
            seen = set()
            unique = []
            for rec in posts[key]:
                rec_key = (rec.source, rec.record_id)
                if rec_key not in seen:
                    seen.add(rec_key)
                    unique.append(rec)
            posts[key] = unique

        # Deduplicate by user: keep only the oldest record per user per X post.
        # This avoids flagging the same user's duplicate submissions as cross-user dupes.
        for key in list(posts.keys()):
            by_user = defaultdict(list)
            for rec in posts[key]:
                by_user[rec.user_id].append(rec)
            unique_users = []
            for user_recs in by_user.values():
                user_recs.sort(key=lambda r: r.created_at)
                unique_users.append(user_recs[0])
            posts[key] = unique_users

        # Filter to only cross-user duplicates (>1 distinct user for same post)
        duplicates = {
            key: items for key, items in posts.items()
            if len(items) > 1
        }

        if not duplicates:
            self.stdout.write(self.style.SUCCESS('No duplicate X posts found.'))
            return

        # Sort each group by created_at (oldest first = legitimate owner)
        for key in duplicates:
            duplicates[key].sort(key=lambda r: r.created_at)

        if csv_output:
            self._output_csv(duplicates)
        else:
            self._output_table(duplicates)

    def _output_table(self, duplicates):
        total_dupes = sum(len(items) - 1 for items in duplicates.values())
        self.stdout.write(
            f'\nFound {len(duplicates)} X posts with cross-user duplicates '
            f'({total_dupes} duplicate submissions total)\n'
        )
        self.stdout.write('=' * 100)

        for (username, status_id), items in sorted(
            duplicates.items(),
            key=lambda x: len(x[1]),
            reverse=True,
        ):
            self.stdout.write(
                f'\nhttps://x.com/{username}/status/{status_id}  '
                f'({len(items)} users)'
            )
            self.stdout.write('-' * 80)

            for i, rec in enumerate(items):
                label = self.style.SUCCESS('OWNER') if i == 0 else self.style.ERROR('DUPE ')
                src = 'C' if rec.source == 'contribution' else 'S'
                self.stdout.write(
                    f'  {label}  [{src}] {rec.state:<12}  '
                    f'{rec.created_at.strftime("%Y-%m-%d %H:%M")}  '
                    f'{rec.user_display:<30}  '
                    f'id={rec.record_id}'
                )

        self.stdout.write('')

    def _output_csv(self, duplicates):
        self.stdout.write(
            'x_url,status_id,is_owner,source,record_id,state,user_display,created_at'
        )
        for (username, status_id), items in duplicates.items():
            url = f'https://x.com/{username}/status/{status_id}'
            for i, rec in enumerate(items):
                is_owner = 'true' if i == 0 else 'false'
                self.stdout.write(
                    f'{url},{status_id},{is_owner},{rec.source},{rec.record_id},'
                    f'{rec.state},{rec.user_display},{rec.created_at.isoformat()}'
                )
