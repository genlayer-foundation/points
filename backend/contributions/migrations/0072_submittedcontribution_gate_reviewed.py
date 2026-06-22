from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0071_metrics_query_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='submittedcontribution',
            name='gate_reviewed',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='True once AI review has checked this submission for automated gate rejects.',
            ),
        ),
    ]
