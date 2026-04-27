from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0045_create_community_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='contributiontype',
            name='required_social_accounts',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="List of required social accounts for submission: 'twitter', 'discord', 'github'",
            ),
        ),
    ]
