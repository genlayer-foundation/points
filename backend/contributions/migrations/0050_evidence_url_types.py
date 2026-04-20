# Combined migration: schema + seed data + normalized_url field + backfill

import django.db.models.deletion
from django.db import migrations, models


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
        'name': 'GitHub Repository',
        'slug': 'github-repo',
        'description': 'A GitHub repository',
        'url_patterns': [
            r'^https?://github\.com/[^/]+/[^/]+/?$',
            r'^https?://github\.com/[^/]+/[^/]+/?#',
        ],
        'is_generic': False,
        'order': 2,
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
        'order': 3,
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
        'order': 4,
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
        'order': 5,
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
        'order': 6,
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

# Slugs that were in earlier iterations but should not exist
REMOVED_SLUGS = ['medium-article', 'blog-post', 'youtube-video', 'deployed-app']


def seed_evidence_url_types(apps, schema_editor):
    EvidenceURLType = apps.get_model('contributions', 'EvidenceURLType')

    # Remove types that should not exist
    EvidenceURLType.objects.filter(slug__in=REMOVED_SLUGS).delete()

    for data in EVIDENCE_URL_TYPES:
        EvidenceURLType.objects.update_or_create(
            slug=data['slug'],
            defaults=data,
        )


def reverse_seed(apps, schema_editor):
    EvidenceURLType = apps.get_model('contributions', 'EvidenceURLType')
    slugs = [t['slug'] for t in EVIDENCE_URL_TYPES]
    EvidenceURLType.objects.filter(slug__in=slugs).delete()


def backfill_normalized_urls(apps, schema_editor):
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
        ('contributions', '0049_featuredcontent_status_field'),
    ]

    operations = [
        # 1. Create EvidenceURLType model
        migrations.CreateModel(
            name='EvidenceURLType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
                ('url_patterns', models.JSONField(default=list, help_text='List of regex patterns to match URLs of this type')),
                ('is_generic', models.BooleanField(default=False, help_text='If True, this is the fallback type for unrecognized URLs')),
                ('order', models.PositiveIntegerField(default=0)),
                ('handle_extract_pattern', models.CharField(blank=True, help_text="Regex with named group 'handle' to extract owner/handle from URL", max_length=500)),
                ('ownership_social_account', models.CharField(blank=True, help_text="Social account type for ownership checks: 'twitter' or 'github'", max_length=20)),
            ],
            options={
                'verbose_name': 'Evidence URL Type',
                'verbose_name_plural': 'Evidence URL Types',
                'ordering': ['order', 'name'],
            },
        ),
        # 2. Add M2M on ContributionType
        migrations.AddField(
            model_name='contributiontype',
            name='accepted_evidence_url_types',
            field=models.ManyToManyField(blank=True, help_text='Accepted evidence URL types. Empty means all types are accepted.', related_name='contribution_types', to='contributions.evidenceurltype'),
        ),
        # 2b. Add "required" M2M on ContributionType: at least one submitted
        #     URL must match one of these; required types are implicitly accepted.
        migrations.AddField(
            model_name='contributiontype',
            name='required_evidence_url_types',
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    'If set, at least one submitted evidence URL must match one of '
                    'these types. Required types are implicitly accepted.'
                ),
                related_name='required_by_contribution_types',
                to='contributions.evidenceurltype',
            ),
        ),
        # 3. Add FK on Evidence
        migrations.AddField(
            model_name='evidence',
            name='url_type',
            field=models.ForeignKey(blank=True, help_text='Auto-detected URL type for this evidence', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='evidence_items', to='contributions.evidenceurltype'),
        ),
        # 4. Add normalized_url field
        migrations.AddField(
            model_name='evidence',
            name='normalized_url',
            field=models.CharField(blank=True, db_index=True, help_text='Normalized URL for fast duplicate detection', max_length=2000),
        ),
        # 5. Seed URL types (and clean up removed ones)
        migrations.RunPython(seed_evidence_url_types, reverse_seed),
        # 6. Backfill normalized URLs
        migrations.RunPython(backfill_normalized_urls, migrations.RunPython.noop),
    ]
