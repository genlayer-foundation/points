from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0053_add_show_in_contributions'),
    ]

    operations = [
        migrations.AddField(
            model_name='submittedcontribution',
            name='is_interesting',
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text='Internal-only flag stewards can toggle to mark a submission as interesting.',
            ),
        ),
    ]
