from django.db import migrations


def backfill_normalized_urls(apps, schema_editor):
    """Backfill normalized_url for all existing Evidence rows with a URL."""
    from contributions.url_utils import normalize_url

    Evidence = apps.get_model('contributions', 'Evidence')
    batch = []
    for evidence in Evidence.objects.exclude(url='').iterator(chunk_size=500):
        evidence.normalized_url = normalize_url(evidence.url)
        batch.append(evidence)
        if len(batch) >= 500:
            Evidence.objects.bulk_update(batch, ['normalized_url'])
            batch = []
    if batch:
        Evidence.objects.bulk_update(batch, ['normalized_url'])


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0052_add_normalized_url_to_evidence'),
    ]

    operations = [
        migrations.RunPython(backfill_normalized_urls, migrations.RunPython.noop),
    ]
