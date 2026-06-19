from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_ensure_project_participants_table'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='view_url',
            field=models.CharField(blank=True, help_text='Optional dedicated Portal view URL for selected projects', max_length=500),
        ),
    ]
