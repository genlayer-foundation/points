from django.core.management.base import BaseCommand

from social_connections.earned_roles import assign_earned_community_roles


class Command(BaseCommand):
    help = 'Assign earned community Discord roles (Synapse/Brain) to qualifying users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Evaluate thresholds and list would-be assignments without calling Discord',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        stats = assign_earned_community_roles(dry_run=dry_run)

        for assignment in stats['assignments']:
            self.stdout.write(
                f"{assignment['role']}: {assignment['user_name']} "
                f"(@{assignment['discord_username']}) — "
                f"{assignment['total_points']} CP, {assignment['poap_count']} POAPs"
            )

        prefix = 'Would assign' if dry_run else 'Assigned'
        summary = (
            f"{prefix} {stats['synapse_assigned']} Synapse and {stats['brain_assigned']} Brain roles "
            f"({stats['checked']} connections checked, "
            f"{stats['skipped_not_member']} not guild members, "
            f"{stats['errors']} errors)"
        )
        if stats['aborted']:
            self.stdout.write(self.style.WARNING(summary + ' — run ABORTED early, see logs'))
        else:
            self.stdout.write(self.style.SUCCESS(summary))
