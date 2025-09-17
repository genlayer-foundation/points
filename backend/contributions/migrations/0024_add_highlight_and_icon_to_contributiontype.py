from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0023_make_points_fields_editable'),
    ]

    operations = [
        migrations.AddField(
            model_name='contributiontype',
            name='is_highlight',
            field=models.BooleanField(default=False, help_text='Marks this type as a highlight category/type'),
        ),
        migrations.AddField(
            model_name='contributiontype',
            name='icon',
            field=models.CharField(blank=True, default='', help_text="Icon identifier (e.g., 'mdi:star', 'fa-solid fa-star')", max_length=100),
        ),
    ]
