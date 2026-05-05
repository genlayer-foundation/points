from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0055_evidenceurltype_allow_duplicate'),
    ]

    operations = [
        migrations.AddField(
            model_name='submittedcontribution',
            name='has_appeal',
            field=models.BooleanField(
                default=False,
                help_text='True once the submitter has appealed a rejection. Each submission can only be appealed once.',
            ),
        ),
        migrations.AddField(
            model_name='submittedcontribution',
            name='appeal_reason',
            field=models.TextField(
                blank=True,
                help_text='Reason provided by the submitter when appealing a rejection.',
            ),
        ),
    ]
