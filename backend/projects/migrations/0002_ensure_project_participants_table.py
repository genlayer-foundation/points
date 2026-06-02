from django.db import migrations


def ensure_project_participants_table(apps, schema_editor):
    Project = apps.get_model('projects', 'Project')
    through_model = Project.participants.through
    table_name = through_model._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        existing_tables = schema_editor.connection.introspection.table_names(cursor)

    if table_name not in existing_tables:
        schema_editor.create_model(through_model)


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            ensure_project_participants_table,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
