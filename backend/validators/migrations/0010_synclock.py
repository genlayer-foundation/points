from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('validators', '0009_per_network_node_versions'),
    ]

    operations = [
        migrations.CreateModel(
            name='SyncLock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('owner_token', models.CharField(blank=True, db_index=True, max_length=32, null=True)),
                ('acquired_at', models.DateTimeField(blank=True, null=True)),
                ('heartbeat_at', models.DateTimeField(blank=True, null=True)),
                ('released_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'validators_sync_lock',
            },
        ),
    ]
