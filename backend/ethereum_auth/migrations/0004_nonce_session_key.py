from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ethereum_auth', '0003_pendingwalletsignup_emailverificationtoken'),
    ]

    operations = [
        migrations.AddField(
            model_name='nonce',
            name='session_key',
            field=models.CharField(blank=True, db_index=True, default='', max_length=64),
            preserve_default=False,
        ),
    ]
