from django.db import migrations


def cleanup_legacy_whats_new_columns(apps, schema_editor):
    """Clean up columns from earlier local versions of migration 0004.

    Some developer databases already applied an older 0004 before the
    What's New schema was simplified. The migration graph now matches the
    simplified models, so this migration only reconciles those existing
    databases at the SQL level.
    """
    connection = schema_editor.connection
    quote = schema_editor.quote_name

    with connection.cursor() as cursor:
        table_names = set(connection.introspection.table_names(cursor))

        if 'notifications_whatsnewannouncement' in table_names:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor,
                    'notifications_whatsnewannouncement',
                )
            }
            for column_name in ('target_selector', 'spotlight_label', 'linked_notification_id'):
                if column_name in columns:
                    schema_editor.execute(
                        f'ALTER TABLE {quote("notifications_whatsnewannouncement")} '
                        f'DROP COLUMN {quote(column_name)}'
                    )

        if 'notifications_whatsnewannouncementseen' in table_names:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor,
                    'notifications_whatsnewannouncementseen',
                )
            }

            if 'seen_at' in columns:
                schema_editor.execute(
                    f'ALTER TABLE {quote("notifications_whatsnewannouncementseen")} '
                    f'DROP COLUMN {quote("seen_at")}'
                )

            schema_editor.execute(
                f'CREATE INDEX IF NOT EXISTS {quote("notificatio_user_id_010262_idx")} '
                f'ON {quote("notifications_whatsnewannouncementseen")} '
                f'({quote("user_id")}, {quote("created_at")})'
            )
            schema_editor.execute(
                f'DROP INDEX IF EXISTS {quote("notificatio_user_id_e53a01_idx")}'
            )


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0004_whatsnewannouncement_whatsnewannouncementseen_and_more'),
    ]

    operations = [
        migrations.RunPython(cleanup_legacy_whats_new_columns, migrations.RunPython.noop),
    ]
