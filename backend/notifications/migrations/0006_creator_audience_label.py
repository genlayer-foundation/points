from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0005_cleanup_legacy_whatsnew_columns'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='audience',
            field=models.CharField(
                choices=[
                    ('all', 'All users'),
                    ('validators', 'Validators'),
                    ('stewards', 'Stewards'),
                    ('builders', 'Builders'),
                    ('community', 'Creators'),
                ],
                db_index=True,
                default='all',
                help_text='Only meaningful for broadcast notifications.',
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name='whatsnewannouncement',
            name='audience',
            field=models.CharField(
                choices=[
                    ('all', 'All users'),
                    ('validators', 'Validators'),
                    ('stewards', 'Stewards'),
                    ('builders', 'Builders'),
                    ('community', 'Creators'),
                ],
                db_index=True,
                default='all',
                max_length=16,
            ),
        ),
    ]
