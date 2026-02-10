from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0030_startuprequest'),
    ]

    operations = [
        migrations.RenameField(
            model_name='submittedcontribution',
            old_name='suggested_points',
            new_name='proposed_points',
        ),
    ]
