from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError
from django.test import SimpleTestCase

from utils.management.commands import migrate_with_lock
from utils.management.commands.migrate_with_lock import Command


def _command_options(**overrides):
    options = {
        'app_label': None,
        'migration_name': None,
        'database': 'default',
        'interactive': False,
        'fake': False,
        'fake_initial': False,
        'plan': False,
        'check_unapplied': False,
        'prune': False,
        'lock_timeout_seconds': 5,
        'lock_poll_seconds': 0.01,
        'verbosity': 1,
    }
    options.update(overrides)
    return options


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params):
        self.connection.executed.append((sql, params))
        self.result = self.connection.results.pop(0)

    def fetchone(self):
        return [self.result]


class FakeConnection:
    def __init__(self, vendor='postgresql', results=None):
        self.vendor = vendor
        self.results = list(results or [])
        self.executed = []
        self.ensure_connection_calls = 0

    def ensure_connection(self):
        self.ensure_connection_calls += 1

    def cursor(self):
        return FakeCursor(self)


class MigrateWithLockCommandTests(SimpleTestCase):
    def run_command(self, connection, **options):
        stdout = StringIO()
        stderr = StringIO()
        command = Command(stdout=stdout, stderr=stderr)
        with patch.object(migrate_with_lock, 'connections', {'default': connection}):
            with patch.object(migrate_with_lock, 'call_command') as call_command:
                command.handle(**_command_options(**options))
                return call_command, stdout.getvalue(), stderr.getvalue()

    def test_non_postgres_runs_migrate_without_lock(self):
        connection = FakeConnection(vendor='sqlite')

        call_command, stdout, _stderr = self.run_command(connection)

        self.assertIn('without advisory lock', stdout)
        self.assertEqual(connection.executed, [])
        call_command.assert_called_once()

    def test_postgres_runs_migrate_inside_advisory_lock(self):
        connection = FakeConnection(results=[True, True])

        call_command, stdout, _stderr = self.run_command(connection)

        self.assertEqual(connection.ensure_connection_calls, 1)
        self.assertIn('Acquired PostgreSQL migration advisory lock', stdout)
        self.assertIn('Released PostgreSQL migration advisory lock', stdout)
        self.assertEqual(connection.executed[0][0], 'SELECT pg_try_advisory_lock(%s, %s)')
        self.assertEqual(connection.executed[1][0], 'SELECT pg_advisory_unlock(%s, %s)')
        call_command.assert_called_once()

    def test_postgres_releases_lock_when_migrate_fails(self):
        connection = FakeConnection(results=[True, True])
        command = Command(stdout=StringIO(), stderr=StringIO())

        with patch.object(migrate_with_lock, 'connections', {'default': connection}):
            with patch.object(migrate_with_lock, 'call_command', side_effect=RuntimeError('boom')):
                with self.assertRaises(RuntimeError):
                    command.handle(**_command_options())

        self.assertEqual(connection.executed[0][0], 'SELECT pg_try_advisory_lock(%s, %s)')
        self.assertEqual(connection.executed[1][0], 'SELECT pg_advisory_unlock(%s, %s)')

    def test_postgres_times_out_when_lock_is_not_available(self):
        connection = FakeConnection(results=[False])
        command = Command(stdout=StringIO(), stderr=StringIO())

        with patch.object(migrate_with_lock, 'connections', {'default': connection}):
            with patch.object(migrate_with_lock, 'call_command') as call_command:
                with self.assertRaises(CommandError):
                    command.handle(**_command_options(lock_timeout_seconds=0))

        call_command.assert_not_called()
        self.assertEqual(connection.executed[0][0], 'SELECT pg_try_advisory_lock(%s, %s)')
