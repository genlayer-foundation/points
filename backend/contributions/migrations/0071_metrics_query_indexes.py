from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0070_fix_community_link_rewards'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='contribution',
            index=models.Index(
                fields=['created_at'],
                name='contrib_created_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='submittedcontribution',
            index=models.Index(
                fields=['created_at'],
                name='sub_created_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='submittedcontribution',
            index=models.Index(
                fields=['state', 'created_at'],
                name='sub_state_created_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='submittedcontribution',
            index=models.Index(
                fields=['state', 'reviewed_at'],
                name='sub_state_reviewed_idx',
            ),
        ),
    ]
