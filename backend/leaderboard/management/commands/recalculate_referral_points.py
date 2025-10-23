import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import User
from leaderboard.models import ReferralPoints, recalculate_referrer_points

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Recalculate all referral points from scratch based on actual contribution data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))

        self.stdout.write(self.style.SUCCESS('Starting referral points recalculation...'))

        try:
            # Get all users who have referred at least one person
            referrers = User.objects.filter(referrals__isnull=False).distinct()
            total_referrers = referrers.count()

            self.stdout.write(f'Found {total_referrers} users with referrals')

            if not dry_run:
                with transaction.atomic():
                    # Delete all existing referral points
                    deleted_count = ReferralPoints.objects.all().count()
                    ReferralPoints.objects.all().delete()
                    self.stdout.write(f'Deleted {deleted_count} existing referral point records')

                    # Recalculate for each referrer
                    updated_count = 0
                    for referrer in referrers:
                        old_builder = 0
                        old_validator = 0

                        # Recalculate
                        recalculate_referrer_points(referrer)

                        # Get new values
                        try:
                            rp = referrer.referral_points
                            new_builder = rp.builder_points
                            new_validator = rp.validator_points

                            self.stdout.write(
                                f'  {referrer.name or referrer.address[:20]}: '
                                f'Builder: {new_builder}, Validator: {new_validator}'
                            )
                            updated_count += 1
                        except ReferralPoints.DoesNotExist:
                            pass

                    self.stdout.write(self.style.SUCCESS(
                        f'\nRecalculated referral points for {updated_count}/{total_referrers} referrers'
                    ))
            else:
                # Dry run - just show what would happen
                for referrer in referrers:
                    # Get current values
                    try:
                        current_rp = referrer.referral_points
                        current_builder = current_rp.builder_points
                        current_validator = current_rp.validator_points
                    except ReferralPoints.DoesNotExist:
                        current_builder = 0
                        current_validator = 0

                    # Calculate what new values would be (without saving)
                    # NOTE: Exclude builder-welcome/validator-waitlist unless referred user has other contributions
                    from contributions.models import Contribution
                    from django.db.models import Sum

                    referred_user_ids = list(User.objects.filter(referred_by=referrer).values_list('id', flat=True))

                    if referred_user_ids:
                        # Calculate builder points with check for other contributions
                        builder_contributions = Contribution.objects.filter(
                            user_id__in=referred_user_ids,
                            contribution_type__category__slug='builder'
                        )

                        builder_points = 0
                        for user_id in referred_user_ids:
                            user_contribs = builder_contributions.filter(user_id=user_id)
                            has_other_builder = user_contribs.exclude(
                                contribution_type__slug='builder-welcome'
                            ).exists()

                            if has_other_builder:
                                builder_points += user_contribs.aggregate(
                                    Sum('frozen_global_points')
                                )['frozen_global_points__sum'] or 0
                            else:
                                builder_points += user_contribs.exclude(
                                    contribution_type__slug='builder-welcome'
                                ).aggregate(
                                    Sum('frozen_global_points')
                                )['frozen_global_points__sum'] or 0

                        new_builder = int(builder_points * 0.1)

                        # Calculate validator points with check for other contributions
                        validator_contributions = Contribution.objects.filter(
                            user_id__in=referred_user_ids,
                            contribution_type__category__slug='validator'
                        )

                        validator_points = 0
                        for user_id in referred_user_ids:
                            user_contribs = validator_contributions.filter(user_id=user_id)
                            has_other_validator = user_contribs.exclude(
                                contribution_type__slug='validator-waitlist'
                            ).exists()

                            if has_other_validator:
                                validator_points += user_contribs.aggregate(
                                    Sum('frozen_global_points')
                                )['frozen_global_points__sum'] or 0
                            else:
                                validator_points += user_contribs.exclude(
                                    contribution_type__slug='validator-waitlist'
                                ).aggregate(
                                    Sum('frozen_global_points')
                                )['frozen_global_points__sum'] or 0

                        new_validator = int(validator_points * 0.1)

                        if new_builder != current_builder or new_validator != current_validator:
                            self.stdout.write(
                                f'  {referrer.name or referrer.address[:20]}: '
                                f'Builder: {current_builder} → {new_builder}, '
                                f'Validator: {current_validator} → {new_validator}'
                            )

                self.stdout.write(self.style.WARNING('\nDRY RUN COMPLETE - Run without --dry-run to apply changes'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error recalculating referral points: {e}'))
            logger.exception('Error in recalculate_referral_points command')
            raise
