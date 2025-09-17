from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0024_add_highlight_and_icon_to_contributiontype'),
    ]

    operations = [
        migrations.AddField(
            model_name='contributiontype',
            name='examples',
            field=models.JSONField(blank=True, default=list, help_text='Example entries for this contribution type (array of short strings)'),
        ),
    ]

