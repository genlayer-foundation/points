from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0023_make_points_fields_editable'),
    ]

    operations = [
        migrations.AddField(
            model_name='contributiontype',
            name='icon',
            field=models.CharField(blank=True, default='', help_text="Icon identifier (e.g., 'mdi:star', 'fa-solid fa-star')", max_length=100),
        ),
        migrations.AddField(
            model_name='contributiontype',
            name='examples',
            field=models.JSONField(blank=True, default=list, help_text='Example entries for this contribution type (array of short strings)'),
        ),
    ]
