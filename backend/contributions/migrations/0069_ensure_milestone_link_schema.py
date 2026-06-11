from django.db import migrations


def ensure_milestone_link_schema(apps, schema_editor):
    """
    Defensive idempotent safeguard for the milestone link fields.

    The original version of 0068 (merged in #768) linked milestones to
    projects.Project through a `project` FK and was rewritten in place to
    link to the accepted Projects contribution via `project_contribution`
    instead. The original never applied successfully in any deployed
    environment (its projects backfill crashed and rolled back atomically),
    but a database that did record it would skip the rewritten 0068 and be
    left with `project_id` columns while the code queries
    `project_contribution_id`. This migration converges any such database to
    the current schema: it drops the legacy `project_id` columns and adds the
    fields the rewritten 0068 defines when they are missing. On databases
    migrated with the rewritten 0068 (or created fresh) it is a no-op.

    The legacy `project_id` values pointed at projects.Project rows, which
    have no reliable mapping to project contributions, so they are dropped
    rather than migrated; any stray showcase Project rows created by the
    original backfill need manual cleanup.
    """
    connection = schema_editor.connection
    Contribution = apps.get_model('contributions', 'Contribution')
    SubmittedContribution = apps.get_model('contributions', 'SubmittedContribution')

    for model in (Contribution, SubmittedContribution):
        table = model._meta.db_table
        with connection.cursor() as cursor:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(cursor, table)
            }

        if 'project_id' in columns:
            schema_editor.execute(
                'ALTER TABLE {table} DROP COLUMN {column}'.format(
                    table=schema_editor.quote_name(table),
                    column=schema_editor.quote_name('project_id'),
                )
            )

        if 'project_contribution_id' not in columns:
            schema_editor.add_field(
                model,
                model._meta.get_field('project_contribution'),
            )

        if 'milestone_version' not in columns:
            schema_editor.add_field(
                model,
                model._meta.get_field('milestone_version'),
            )


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0068_split_projects_and_milestones'),
    ]

    operations = [
        migrations.RunPython(
            ensure_milestone_link_schema,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
