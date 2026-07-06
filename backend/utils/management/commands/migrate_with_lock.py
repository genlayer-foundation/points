import zlib

from django.core.management import BaseCommand, call_command
from django.db import connections


MIGRATION_LOCK_NAMESPACE = 0x54414C59  # "TALY", signed int32-safe.
# ponytail: hardcoded; make it a flag/env var if a deploy ever needs to tune it.
LOCK_TIMEOUT_SECONDS = 900


def _signed_int32(value):
    return value - 2**32 if value >= 2**31 else value


MIGRATION_LOCK_KEY = _signed_int32(zlib.crc32(b'tally:migrations:default'))


class Command(BaseCommand):
    help = 'Run Django migrations under a PostgreSQL advisory lock.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput',
            '--no-input',
            action='store_false',
            dest='interactive',
            default=True,
            help='Do not prompt the user for input.',
        )

    def handle(self, *args, **options):
        connection = connections['default']
        migrate_options = {
            'interactive': options['interactive'],
            'verbosity': options['verbosity'],
            'stdout': self.stdout,
            'stderr': self.stderr,
        }

        if connection.vendor != 'postgresql':
            self.stdout.write(
                f'Database backend is {connection.vendor}; running migrations without advisory lock.'
            )
            call_command('migrate', **migrate_options)
            return

        # Postgres does the waiting: lock_timeout bounds the blocking
        # pg_advisory_lock call, and the session-level lock releases itself
        # when this command's connection closes.
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute(f"SET lock_timeout = '{LOCK_TIMEOUT_SECONDS}s'")
            self.stdout.write('Waiting for PostgreSQL migration advisory lock...')
            cursor.execute(
                'SELECT pg_advisory_lock(%s, %s)',
                [MIGRATION_LOCK_NAMESPACE, MIGRATION_LOCK_KEY],
            )
            cursor.execute('SET lock_timeout = 0')

        self.stdout.write('Acquired PostgreSQL migration advisory lock.')
        call_command('migrate', **migrate_options)
