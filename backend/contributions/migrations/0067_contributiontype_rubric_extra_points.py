from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0066_alter_contributionhighlight_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='contributiontype',
            name='rubric_extra_points',
            field=models.PositiveIntegerField(
                default=2,
                help_text='Points awarded per verified extra in the Builder Project rubric.',
            ),
        ),
    ]
