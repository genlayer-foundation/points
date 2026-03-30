"""
Seed initial blocklisted URL prefixes.
"""

from django.db import migrations


INITIAL_BLOCKLISTED_URLS = [
    {
        'url_prefix': 'https://studio.genlayer.com/run-debug',
        'reason': 'Studio IDE debugging page — not evidence of work',
    },
    {
        'url_prefix': 'https://studio.genlayer.com/contracts',
        'reason': 'Studio contracts editor — not evidence of work',
    },
    {
        'url_prefix': 'https://points.genlayer.foundation',
        'reason': 'The points platform itself — not evidence of work',
    },
    {
        'url_prefix': 'https://www.genlayer.com',
        'reason': 'Main GenLayer website — not evidence of work',
    },
    {
        'url_prefix': 'https://genlayer.com',
        'reason': 'Main GenLayer website — not evidence of work',
    },
]


def seed_urls(apps, schema_editor):
    BlocklistedURL = apps.get_model('contributions', 'BlocklistedURL')
    for entry in INITIAL_BLOCKLISTED_URLS:
        BlocklistedURL.objects.get_or_create(
            url_prefix=entry['url_prefix'],
            defaults={'reason': entry['reason']},
        )


def remove_urls(apps, schema_editor):
    BlocklistedURL = apps.get_model('contributions', 'BlocklistedURL')
    prefixes = [e['url_prefix'] for e in INITIAL_BLOCKLISTED_URLS]
    BlocklistedURL.objects.filter(url_prefix__in=prefixes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0042_blocklisted_url_model'),
    ]

    operations = [
        migrations.RunPython(seed_urls, remove_urls),
    ]
