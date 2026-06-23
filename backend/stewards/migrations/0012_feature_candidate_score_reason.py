from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stewards', '0011_feature_candidate_scoring'),
    ]

    operations = [
        migrations.AddField(
            model_name='featurecandidatescore',
            name='reason',
            field=models.TextField(blank=True, default='', help_text='Reviewer note explaining what stood out for this score.'),
        ),
    ]
