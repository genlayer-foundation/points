from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_ensure_project_participants_table'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='show_in_overview',
            field=models.BooleanField(
                default=False,
                help_text='Show this project in the portal overview featured projects section.',
            ),
        ),
    ]
