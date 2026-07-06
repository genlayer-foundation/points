from io import StringIO
from unittest.mock import patch

from django.test import SimpleTestCase

from utils.management.commands import migrate_with_lock
from utils.management.commands.migrate_with_lock import Command


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params=None):
        self.connection.executed.append((sql, params))


class FakeConnection:
    def __init__(self, vendor='postgresql'):
        self.vendor = vendor
        self.executed = []
        self.ensure_connection_calls = 0

    def ensure_connection(self):
        self.ensure_connection_calls += 1

    def cursor(self):
        return FakeCursor(self)


class MigrateWithLockCommandTests(SimpleTestCase):
    def run_command(self, connection):
        stdout = StringIO()
        command = Command(stdout=stdout, stderr=StringIO())
        with patch.object(migrate_with_lock, 'connections', {'default': connection}):
            with patch.object(migrate_with_lock, 'call_command') as call_command:
                command.handle(interactive=False, verbosity=1)
                return call_command, stdout.getvalue()

    def test_non_postgres_runs_migrate_without_lock(self):
        connection = FakeConnection(vendor='sqlite')

        call_command, stdout = self.run_command(connection)

        self.assertIn('without advisory lock', stdout)
        self.assertEqual(connection.executed, [])
        call_command.assert_called_once()

    def test_postgres_takes_advisory_lock_with_bounded_wait(self):
        connection = FakeConnection()

        call_command, stdout = self.run_command(connection)

        self.assertEqual(connection.ensure_connection_calls, 1)
        self.assertIn('Acquired PostgreSQL migration advisory lock', stdout)
        executed_sql = [sql for sql, _params in connection.executed]
        self.assertEqual(executed_sql, [
            "SET lock_timeout = '900s'",
            'SELECT pg_advisory_lock(%s, %s)',
            'SET lock_timeout = 0',
        ])
        self.assertEqual(
            connection.executed[1][1],
            [migrate_with_lock.MIGRATION_LOCK_NAMESPACE, migrate_with_lock.MIGRATION_LOCK_KEY],
        )
        call_command.assert_called_once()
