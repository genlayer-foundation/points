from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ethereum_auth', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='nonce',
            name='purpose',
            field=models.CharField(
                choices=[
                    ('login', 'Login'),
                    ('poap_recovery', 'POAP Recovery'),
                ],
                db_index=True,
                default='login',
                max_length=32,
            ),
        ),
    ]
