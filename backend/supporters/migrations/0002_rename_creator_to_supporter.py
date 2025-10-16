# Safe migration for renaming Creator to Supporter
# Preserves existing database table name to avoid breaking production
# Note: App label is 'creators' for backward compatibility, even though folder is 'supporters'

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('creators', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Rename the model from Creator to Supporter
        # This only changes the Python model name, not the database table
        migrations.RenameModel(
            old_name='Creator',
            new_name='Supporter',
        ),
        # Explicitly preserve the old table name to maintain compatibility
        migrations.AlterModelTable(
            name='Supporter',
            table='creators_creator',
        ),
        # Update the related_name on the user foreign key
        migrations.AlterField(
            model_name='supporter',
            name='user',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='supporter',
                to=settings.AUTH_USER_MODEL
            ),
        ),
    ]
