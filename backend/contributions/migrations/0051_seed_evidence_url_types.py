from django.db import migrations


EVIDENCE_URL_TYPES = [
    {
        'name': 'X Post',
        'slug': 'x-post',
        'description': 'A post on X (formerly Twitter)',
        'url_patterns': [
            r'^https?://(www\.)?x\.com/[^/]+/status/\d+',
            r'^https?://(www\.)?twitter\.com/[^/]+/status/\d+',
        ],
        'is_generic': False,
        'order': 1,
        'handle_extract_pattern': r'(?:x|twitter)\.com/(?P<handle>[^/]+)/status/',
        'ownership_social_account': 'twitter',
    },
    {
        'name': 'YouTube Video',
        'slug': 'youtube-video',
        'description': 'A video on YouTube',
        'url_patterns': [
            r'^https?://(www\.)?youtube\.com/watch\?.*v=',
            r'^https?://youtu\.be/.+',
            r'^https?://(www\.)?youtube\.com/shorts/.+',
        ],
        'is_generic': False,
        'order': 2,
        'handle_extract_pattern': '',
        'ownership_social_account': '',
    },
    {
        'name': 'GitHub Repository',
        'slug': 'github-repo',
        'description': 'A GitHub repository',
        'url_patterns': [
            r'^https?://github\.com/[^/]+/[^/]+/?$',
            r'^https?://github\.com/[^/]+/[^/]+/?#',
        ],
        'is_generic': False,
        'order': 3,
        'handle_extract_pattern': r'github\.com/(?P<handle>[^/]+)/',
        'ownership_social_account': 'github',
    },
    {
        'name': 'GitHub File',
        'slug': 'github-file',
        'description': 'A file in a GitHub repository',
        'url_patterns': [
            r'^https?://github\.com/[^/]+/[^/]+/blob/.+',
        ],
        'is_generic': False,
        'order': 4,
        'handle_extract_pattern': r'github\.com/(?P<handle>[^/]+)/',
        'ownership_social_account': 'github',
    },
    {
        'name': 'GitHub Pull Request',
        'slug': 'github-pr',
        'description': 'A pull request on GitHub',
        'url_patterns': [
            r'^https?://github\.com/[^/]+/[^/]+/pull/\d+',
        ],
        'is_generic': False,
        'order': 5,
        'handle_extract_pattern': '',
        'ownership_social_account': '',
    },
    {
        'name': 'GitHub Issue',
        'slug': 'github-issue',
        'description': 'An issue on GitHub',
        'url_patterns': [
            r'^https?://github\.com/[^/]+/[^/]+/issues/\d+',
        ],
        'is_generic': False,
        'order': 6,
        'handle_extract_pattern': '',
        'ownership_social_account': '',
    },
    {
        'name': 'GenLayer Studio Contract',
        'slug': 'studio-contract',
        'description': 'A smart contract deployed on GenLayer Studio',
        'url_patterns': [
            r'^https?://studio\.genlayer\.com/contracts\?.*import-contract=0x[0-9a-fA-F]{40}',
        ],
        'is_generic': False,
        'order': 7,
        'handle_extract_pattern': '',
        'ownership_social_account': '',
    },
    {
        'name': 'Other',
        'slug': 'other',
        'description': 'Any URL that does not match a specific evidence type',
        'url_patterns': [],
        'is_generic': True,
        'order': 100,
        'handle_extract_pattern': '',
        'ownership_social_account': '',
    },
]


def seed_evidence_url_types(apps, schema_editor):
    EvidenceURLType = apps.get_model('contributions', 'EvidenceURLType')
    for data in EVIDENCE_URL_TYPES:
        EvidenceURLType.objects.update_or_create(
            slug=data['slug'],
            defaults=data,
        )


def reverse_seed(apps, schema_editor):
    EvidenceURLType = apps.get_model('contributions', 'EvidenceURLType')
    slugs = [t['slug'] for t in EVIDENCE_URL_TYPES]
    EvidenceURLType.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0050_evidence_url_type_model'),
    ]

    operations = [
        migrations.RunPython(seed_evidence_url_types, reverse_seed),
    ]
