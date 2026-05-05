from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('validators', '0010_synclock'),
    ]

    operations = [
        migrations.AddField(
            model_name='validator',
            name='display_order',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Lower numbers appear first on the Ecosystem page. Ties fall back to newest-first.',
            ),
        ),
    ]
