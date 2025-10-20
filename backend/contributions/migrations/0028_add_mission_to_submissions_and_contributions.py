# Generated migration

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0027_alter_evidence_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='submittedcontribution',
            name='mission',
            field=models.ForeignKey(
                blank=True,
                help_text='Mission that prompted this submission (optional)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='submissions',
                to='contributions.mission'
            ),
        ),
        migrations.AddField(
            model_name='contribution',
            name='mission',
            field=models.ForeignKey(
                blank=True,
                help_text='Mission this contribution fulfills (optional)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='contributions',
                to='contributions.mission'
            ),
        ),
    ]
