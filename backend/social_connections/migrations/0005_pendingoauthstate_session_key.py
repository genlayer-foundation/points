from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('social_connections', '0004_pendingoauthstate'),
    ]

    operations = [
        migrations.AddField(
            model_name='pendingoauthstate',
            name='session_key',
            field=models.CharField(blank=True, db_index=True, default='', max_length=64),
            preserve_default=False,
        ),
        migrations.AddIndex(
            model_name='pendingoauthstate',
            index=models.Index(fields=['platform', 'session_key'], name='social_conn_platfor_21c924_idx'),
        ),
    ]
