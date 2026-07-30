"""
Functional index on UPPER(address).

Built CONCURRENTLY on PostgreSQL: startup.sh runs migrate_with_lock on every
container start with lock_timeout = 0, so a plain CREATE INDEX would take an
ACCESS EXCLUSIVE lock and could wait indefinitely behind a long-running query,
stalling the deploy. A concurrent build takes no exclusive lock.

Other backends (SQLite in local dev and CI) get the ordinary index, since
CONCURRENTLY is PostgreSQL-only. The state operation is shared, so model state
and migration state agree on every backend and `makemigrations --check` stays
clean.
"""

import django.db.models.functions.text
from django.db import migrations, models


INDEX_NAME = 'users_user_address_upper_idx'


def _index_is_invalid(schema_editor):
    """
    True when the index exists but is marked invalid.

    An interrupted CREATE INDEX CONCURRENTLY leaves the index in the catalog
    with indisvalid = false. The planner ignores it, but it still carries write
    overhead, and a retried CREATE INDEX CONCURRENTLY IF NOT EXISTS silently
    skips rather than rebuilding it, so the lookups would stay unindexed.
    """
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            'SELECT indisvalid FROM pg_index WHERE indexrelid = to_regclass(%s)',
            [INDEX_NAME],
        )
        row = cursor.fetchone()
    return row is not None and row[0] is False


def create_index(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        schema_editor.execute(
            f'CREATE INDEX IF NOT EXISTS {INDEX_NAME} ON users_user (UPPER(address))'
        )
        return

    if _index_is_invalid(schema_editor):
        # Clear the leftover first; IF NOT EXISTS would skip over it.
        schema_editor.execute(f'DROP INDEX CONCURRENTLY IF EXISTS {INDEX_NAME}')

    schema_editor.execute(
        f'CREATE INDEX CONCURRENTLY IF NOT EXISTS {INDEX_NAME} '
        'ON users_user (UPPER(address))'
    )


def drop_index(apps, schema_editor):
    concurrently = 'CONCURRENTLY ' if schema_editor.connection.vendor == 'postgresql' else ''
    schema_editor.execute(f'DROP INDEX {concurrently}IF EXISTS {INDEX_NAME}')


class Migration(migrations.Migration):
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction.
    atomic = False

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('users', '0021_user_can_view_role_sections'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddIndex(
                    model_name='user',
                    index=models.Index(
                        django.db.models.functions.text.Upper('address'),
                        name=INDEX_NAME,
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(create_index, drop_index),
            ],
        ),
    ]
