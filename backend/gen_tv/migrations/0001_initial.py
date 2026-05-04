from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Stream',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=300)),
                ('slug', models.SlugField(max_length=300, unique=True)),
                ('description', models.TextField(blank=True)),
                ('url', models.URLField(help_text='Source URL (X / Twitter, YouTube, etc.).', max_length=500)),
                ('image_url', models.URLField(blank=True, help_text='Thumbnail / cover image URL.', max_length=500)),
                ('starts_at', models.DateTimeField(help_text='Scheduled start time (used for sorting and status).')),
                ('ends_at', models.DateTimeField(help_text='Scheduled end time (used to compute status and the duration badge).')),
                ('category', models.CharField(choices=[('internal', 'GenLayer Team'), ('community', 'Community')], max_length=20)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['-starts_at'],
            },
        ),
    ]
