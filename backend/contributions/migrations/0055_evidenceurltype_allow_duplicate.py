from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0054_submittedcontribution_is_interesting'),
    ]

    operations = [
        migrations.AddField(
            model_name='evidenceurltype',
            name='allow_duplicate',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'If True, URLs of this type are exempt from duplicate '
                    'checking against other submissions and contributions. '
                    'Useful for shared resources like GitHub repositories.'
                ),
            ),
        ),
    ]
