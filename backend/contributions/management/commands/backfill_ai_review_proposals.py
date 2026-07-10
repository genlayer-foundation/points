from django.core.management.base import BaseCommand
from django.db import transaction

from contributions.ai_attribution import get_ai_steward
from contributions.models import ReviewProposal, SubmittedContribution


class Command(BaseCommand):
    help = (
        'Backfill ReviewProposal AI snapshot rows for pending submissions whose '
        'active proposal was made by the AI steward before snapshot tracking '
        'existed, so they match the is:ai-reviewed filter. Idempotent.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List the submissions that would be backfilled without writing.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        ai_user = get_ai_steward()

        submissions = (
            SubmittedContribution.objects
            .filter(
                state='pending',
                proposed_by=ai_user,
                project_milestone_review__isnull=False,
            )
            .exclude(review_proposals__source=ReviewProposal.SOURCE_AI)
            .select_related('project_milestone_review')
        )

        created = 0
        for submission in submissions:
            if dry_run:
                self.stdout.write(f'Would backfill {submission.id}')
                created += 1
                continue

            rubric = submission.project_milestone_review
            proposal_note = (
                submission.internal_notes
                .filter(user=ai_user, is_proposal=True)
                .order_by('-created_at')
                .first()
            )
            row = ReviewProposal.objects.create(
                submitted_contribution=submission,
                proposer=ai_user,
                source=ReviewProposal.SOURCE_AI,
                service_account_name=(
                    (proposal_note.data or {}).get('service_account', '')
                    if proposal_note else ''
                ),
                action=submission.proposed_action,
                points=submission.proposed_points,
                staff_reply=submission.proposed_staff_reply or '',
                confidence=submission.proposed_confidence,
                gate_failures=rubric.gate_failures,
                sections=rubric.sections,
                extras=rubric.extras,
                overall_reason=rubric.overall_reason,
                # ponytail: no synthesis existed pre-pipeline; a later AI PUT re-propose adds it
            )
            if submission.proposed_at:
                # Keep the analysis timestamp truthful (created_at is auto_now_add)
                ReviewProposal.objects.filter(pk=row.pk).update(
                    created_at=submission.proposed_at
                )
            created += 1
            self.stdout.write(f'Backfilled {submission.id}')

        verb = 'Would backfill' if dry_run else 'Backfilled'
        self.stdout.write(self.style.SUCCESS(f'{verb} {created} submission(s)'))
