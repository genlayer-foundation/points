from django.db import migrations


EXPLORER = {
    'name': 'GenLayer Explorer Contract',
    'slug': 'genlayer-explorer-contract',
    'description': 'A deployed contract address on a GenLayer explorer '
                   '(Asimov, Bradbury, Studio explorer, Testnet)',
    'url_patterns': [
        r'^https?://explorer[.-][a-z0-9.-]+\.genlayer\.com/address/0x[0-9a-fA-F]{40}\b',
    ],
    'is_generic': False,
    'order': 7,
    'handle_extract_pattern': '',
    'ownership_social_account': '',
    'allow_duplicate': False,
}

# Stricter Studio pattern: require import-contract to be a real query param
# (start of query or after '&'), not merely a substring like fake-import-contract.
STUDIO_NEW = [r'^https?://studio\.genlayer\.com/contracts\?(?:[^#]*&)?import-contract=0x[0-9a-fA-F]{40}\b']
STUDIO_OLD = [r'^https?://studio\.genlayer\.com/contracts\?.*import-contract=0x[0-9a-fA-F]{40}']


def forwards(apps, schema_editor):
    EvidenceURLType = apps.get_model('contributions', 'EvidenceURLType')
    EvidenceURLType.objects.update_or_create(slug=EXPLORER['slug'], defaults=EXPLORER)
    EvidenceURLType.objects.filter(slug='studio-contract').update(url_patterns=STUDIO_NEW)


def backwards(apps, schema_editor):
    EvidenceURLType = apps.get_model('contributions', 'EvidenceURLType')
    EvidenceURLType.objects.filter(slug=EXPLORER['slug']).delete()
    EvidenceURLType.objects.filter(slug='studio-contract').update(url_patterns=STUDIO_OLD)


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0075_contributiontype_required_evidence_url_type_groups'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
