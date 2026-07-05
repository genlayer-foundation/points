import os
import time
import zlib

from django.core.management import BaseCommand, CommandError, call_command
from django.db import connections


MIGRATION_LOCK_NAMESPACE = 0x54414C59  # "TALY", signed int32-safe.


def _env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _signed_int32(value):
    return value - 2**32 if value >= 2**31 else value


def _migration_lock_key(database_alias):
    return _signed_int32(zlib.crc32(f'tally:migrations:{database_alias}'.encode('utf-8')))


class Command(BaseCommand):
    help = 'Run Django migrations under a PostgreSQL advisory lock.'

    def add_arguments(self, parser):
        parser.add_argument('app_label', nargs='?')
        parser.add_argument('migration_name', nargs='?')
        parser.add_argument(
            '--database',
            default='default',
            help='Database to migrate. Defaults to the "default" database.',
        )
        parser.add_argument(
            '--noinput',
            '--no-input',
            action='store_false',
            dest='interactive',
            default=True,
            help='Do not prompt the user for input.',
        )
        parser.add_argument(
            '--fake',
            action='store_true',
            help='Mark migrations as run without actually running them.',
        )
        parser.add_argument(
            '--fake-initial',
            action='store_true',
            dest='fake_initial',
            help='Detect initial migrations as already applied when tables exist.',
        )
        parser.add_argument(
            '--plan',
            action='store_true',
            help='Show the migration plan instead of running migrations.',
        )
        parser.add_argument(
            '--check',
            action='store_true',
            dest='check_unapplied',
            help='Exit non-zero if unapplied migrations exist.',
        )
        parser.add_argument(
            '--prune',
            action='store_true',
            help='Delete nonexistent migrations from the django_migrations table.',
        )
        parser.add_argument(
            '--lock-timeout-seconds',
            type=float,
            default=_env_float('MIGRATION_LOCK_TIMEOUT_SECONDS', 900),
            help='Seconds to wait for the migration lock before failing.',
        )
        parser.add_argument(
            '--lock-poll-seconds',
            type=float,
            default=_env_float('MIGRATION_LOCK_POLL_SECONDS', 2),
            help='Seconds between migration lock acquisition attempts.',
        )

    def handle(self, *args, **options):
        database = options['database']
        connection = connections[database]
        migrate_args = [
            value for value in (options.get('app_label'), options.get('migration_name')) if value
        ]
        migrate_options = {
            'database': database,
            'interactive': options['interactive'],
            'fake': options['fake'],
            'fake_initial': options['fake_initial'],
            'plan': options['plan'],
            'check_unapplied': options['check_unapplied'],
            'prune': options['prune'],
            'verbosity': options['verbosity'],
            'stdout': self.stdout,
            'stderr': self.stderr,
        }

        if connection.vendor != 'postgresql':
            self.stdout.write(
                f'Database backend is {connection.vendor}; running migrations without advisory lock.'
            )
            call_command('migrate', *migrate_args, **migrate_options)
            return

        timeout_seconds = options['lock_timeout_seconds']
        poll_seconds = options['lock_poll_seconds']
        if timeout_seconds < 0:
            raise CommandError('--lock-timeout-seconds must be >= 0')
        if poll_seconds <= 0:
            raise CommandError('--lock-poll-seconds must be > 0')

        lock_key = _migration_lock_key(database)
        acquired = False
        connection.ensure_connection()
        try:
            self._acquire_lock(connection, lock_key, timeout_seconds, poll_seconds)
            acquired = True
            call_command('migrate', *migrate_args, **migrate_options)
        finally:
            if acquired:
                self._release_lock(connection, lock_key)

    def _acquire_lock(self, connection, lock_key, timeout_seconds, poll_seconds):
        deadline = time.monotonic() + timeout_seconds
        next_notice = 0

        while True:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT pg_try_advisory_lock(%s, %s)',
                    [MIGRATION_LOCK_NAMESPACE, lock_key],
                )
                acquired = cursor.fetchone()[0]

            if acquired:
                self.stdout.write('Acquired PostgreSQL migration advisory lock.')
                return

            now = time.monotonic()
            if now >= deadline:
                raise CommandError(
                    f'Timed out after {timeout_seconds:g}s waiting for migration advisory lock.'
                )

            if now >= next_notice:
                self.stdout.write('Waiting for another instance to finish migrations...')
                next_notice = now + 30

            time.sleep(min(poll_seconds, max(deadline - now, 0)))

    def _release_lock(self, connection, lock_key):
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT pg_advisory_unlock(%s, %s)',
                    [MIGRATION_LOCK_NAMESPACE, lock_key],
                )
                released = cursor.fetchone()[0]
        except Exception as exc:
            self.stderr.write(f'WARNING: could not release migration advisory lock: {exc}')
            return

        if released:
            self.stdout.write('Released PostgreSQL migration advisory lock.')
        else:
            self.stderr.write('WARNING: migration advisory lock was already released.')
