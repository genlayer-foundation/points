from django.db import migrations, models
from django.utils.text import slugify


PARTNERS = [
    ('ZKsync', 'https://www.zksync.io/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777904987/partners/zksync.svg'),
    ('Radix', 'https://www.radixdlt.com/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777904988/partners/radix.svg'),
    ('Autonomys', 'https://www.autonomys.xyz/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777904990/partners/autonomys.svg'),
    ('Nansen', 'https://www.nansen.ai/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777904992/partners/nansen.svg'),
    ('Etherisc', 'https://etherisc.com/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777904994/partners/etherisc.svg'),
    ('PredX', 'https://predx.ai/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777904996/partners/predx.svg'),
    ('Provably', 'https://www.provably.ai/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777904998/partners/provably.svg'),
    ('Peersyst', 'https://peersyst.com/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777904999/partners/peersyst.svg'),
    ('Heurist', 'https://www.heurist.ai/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777905001/partners/heurist.svg'),
    ('Atoma', 'https://www.atoma.network/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777905002/partners/atoma.svg'),
    ('Spheron', 'https://www.spheron.network/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777905004/partners/spheron.svg'),
    ('Hyperbolic', 'https://www.hyperbolic.xyz/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777905006/partners/hyperbolic.svg'),
    ('Chasm', 'https://www.chasm.net/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777905008/partners/chasm.svg'),
    ('Morpheus', 'https://mor.org/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777905009/partners/morpheus.svg'),
    ('DELPHIBETS', 'https://delphibets.com/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777905011/partners/delphibets.svg'),
    ('DIA', 'https://www.diadata.org/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777905014/partners/dia.svg'),
    ('io.net', 'https://io.net/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777905017/partners/ionet.svg'),
    ('Chutes', 'https://chutes.ai/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777905340/chutes_xylxdk.svg'),
    ('Comput3', 'https://comput3.ai/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777905329/comput3_kn5hn0.svg'),
    ('Aleph Cloud', 'https://aleph.cloud/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777905733/aleph-cloud-white_or7gqe.svg'),
    ('LayerZero', 'https://layerzero.network/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777905614/layerzero_tkhkav.svg'),
    ('Base', 'https://base.org/', 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1777907519/base-padded_bvjzlz.svg'),
]

PLACEHOLDER_SLUGS = ['example-partner', 'second-partner']


def seed_partners(apps, schema_editor):
    Partner = apps.get_model('partners', 'Partner')
    Partner.objects.filter(slug__in=PLACEHOLDER_SLUGS).delete()
    for index, (name, website_url, logo_url) in enumerate(PARTNERS):
        slug = slugify(name)
        Partner.objects.update_or_create(
            slug=slug,
            defaults={
                'name': name,
                'website_url': website_url,
                'logo_url': logo_url or '',
                'description': '',
                'display_order': index,
                'is_active': True,
            },
        )


def unseed_partners(apps, schema_editor):
    Partner = apps.get_model('partners', 'Partner')
    slugs = [slugify(name) for name, _, _ in PARTNERS]
    Partner.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Partner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=200, unique=True)),
                ('description', models.TextField(blank=True)),
                ('logo_url', models.URLField(blank=True, max_length=500)),
                ('website_url', models.URLField(help_text='Official website (primary redirect target).', max_length=500)),
                ('url', models.URLField(blank=True, help_text='Optional secondary URL (e.g. integration / deep link).', max_length=500)),
                ('display_order', models.PositiveIntegerField(default=0, help_text='Lower numbers appear first within their group.')),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['display_order', 'name'],
            },
        ),
        migrations.RunPython(seed_partners, unseed_partners),
    ]
