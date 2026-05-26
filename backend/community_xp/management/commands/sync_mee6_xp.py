from django.core.management.base import BaseCommand, CommandError

from community_xp.services import Mee6SyncAlreadyRunning, Mee6SyncError, run_mee6_sync


class Command(BaseCommand):
    help = 'Fetch MEE6 Discord XP snapshots without applying them as the active community XP baseline'

    def add_arguments(self, parser):
        parser.add_argument('--guild-id', default=None, help='Discord guild ID to sync')
        parser.add_argument('--page-size', type=int, default=None, help='MEE6 leaderboard page size')
        parser.add_argument(
            '--no-lock',
            action='store_true',
            help='Run without acquiring the database sync lock',
        )

    def handle(self, *args, **options):
        try:
            result = run_mee6_sync(
                guild_id=options.get('guild_id'),
                page_size=options.get('page_size'),
                use_lock=not options.get('no_lock'),
            )
        except Mee6SyncAlreadyRunning as exc:
            elapsed = f" for {exc.elapsed_seconds:.0f}s" if exc.elapsed_seconds is not None else ''
            raise CommandError(f'MEE6 XP sync already running{elapsed}') from exc
        except Mee6SyncError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(
            'MEE6 XP snapshot fetch completed: '
            f"{result['players_fetched']} players, "
            f"{result['matched_players']} matched, "
            f"{result['unmatched_players']} unmatched, "
            f"{result['pages_fetched']} pages. "
            "Apply this run in Django admin to update portal community scores."
        ))
