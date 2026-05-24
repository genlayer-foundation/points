import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils.text import slugify


def _unique_slug(Project, title, used_slugs, db_alias):
    base_slug = slugify(title)[:200] or 'project'
    slug = base_slug
    suffix = 2
    while slug in used_slugs or Project.objects.using(db_alias).filter(slug=slug).exists():
        suffix_text = f'-{suffix}'
        slug = f'{base_slug[:220 - len(suffix_text)]}{suffix_text}'
        suffix += 1
    used_slugs.add(slug)
    return slug


def copy_featured_builds_to_projects(apps, schema_editor):
    FeaturedContent = apps.get_model('contributions', 'FeaturedContent')
    Contribution = apps.get_model('contributions', 'Contribution')
    Project = apps.get_model('projects', 'Project')
    db_alias = schema_editor.connection.alias
    used_slugs = set()

    featured_builds = FeaturedContent.objects.using(db_alias).filter(
        content_type='build',
    ).order_by('order', 'created_at', 'id')

    for featured in featured_builds:
        project = Project.objects.using(db_alias).create(
            title=featured.title,
            slug=_unique_slug(Project, featured.title, used_slugs, db_alias),
            description=featured.description,
            author=featured.author,
            user_id=featured.user_id,
            hero_image_url=featured.hero_image_url,
            hero_image_public_id=featured.hero_image_public_id,
            hero_image_url_tablet=featured.hero_image_url_tablet,
            hero_image_tablet_public_id=featured.hero_image_tablet_public_id,
            hero_image_url_mobile=featured.hero_image_url_mobile,
            hero_image_mobile_public_id=featured.hero_image_mobile_public_id,
            user_profile_image_url=featured.user_profile_image_url,
            user_profile_image_public_id=featured.user_profile_image_public_id,
            url=featured.url,
            status=featured.status,
            order=featured.order,
        )
        if featured.contribution_id:
            project.related_contributions.add(featured.contribution_id)
            contribution = Contribution.objects.using(db_alias).filter(
                id=featured.contribution_id,
            ).only('user_id').first()
            if contribution and contribution.user_id:
                project.participants.add(contribution.user_id)


def copy_projects_to_featured_builds(apps, schema_editor):
    FeaturedContent = apps.get_model('contributions', 'FeaturedContent')
    Project = apps.get_model('projects', 'Project')
    db_alias = schema_editor.connection.alias

    projects = Project.objects.using(db_alias).all().order_by('order', 'created_at', 'id')
    for project in projects:
        if not project.user_id:
            continue
        contribution = project.related_contributions.order_by('id').first()
        FeaturedContent.objects.using(db_alias).create(
            content_type='build',
            title=project.title,
            description=project.description,
            author=project.author,
            contribution_id=contribution.id if contribution else None,
            user_id=project.user_id,
            hero_image_url=project.hero_image_url,
            hero_image_public_id=project.hero_image_public_id,
            hero_image_url_tablet=project.hero_image_url_tablet,
            hero_image_tablet_public_id=project.hero_image_tablet_public_id,
            hero_image_url_mobile=project.hero_image_url_mobile,
            hero_image_mobile_public_id=project.hero_image_mobile_public_id,
            user_profile_image_url=project.user_profile_image_url,
            user_profile_image_public_id=project.user_profile_image_public_id,
            url=project.url,
            status=project.status,
            order=project.order,
        )


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contributions', '0059_add_canceled_submission_state'),
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=200)),
                ('slug', models.SlugField(blank=True, max_length=220, unique=True)),
                ('description', models.TextField(blank=True)),
                ('author', models.CharField(blank=True, max_length=200)),
                ('hero_image_url', models.URLField(blank=True, help_text='Cloudinary URL for hero image', max_length=500)),
                ('hero_image_public_id', models.CharField(blank=True, help_text='Cloudinary public ID for hero image', max_length=255)),
                ('hero_image_url_tablet', models.URLField(blank=True, help_text='Cloudinary URL for tablet hero image (768-1023px). Falls back to hero_image_url if empty.', max_length=500)),
                ('hero_image_tablet_public_id', models.CharField(blank=True, help_text='Cloudinary public ID for tablet hero image', max_length=255)),
                ('hero_image_url_mobile', models.URLField(blank=True, help_text='Cloudinary URL for mobile hero image (<768px). Falls back to hero_image_url if empty.', max_length=500)),
                ('hero_image_mobile_public_id', models.CharField(blank=True, help_text='Cloudinary public ID for mobile hero image', max_length=255)),
                ('user_profile_image_url', models.URLField(blank=True, help_text='Cloudinary URL for project author image', max_length=500)),
                ('user_profile_image_public_id', models.CharField(blank=True, help_text='Cloudinary public ID for project author image', max_length=255)),
                ('url', models.URLField(blank=True, help_text='Project website or demo URL', max_length=500)),
                ('github_url', models.URLField(blank=True, max_length=500)),
                ('x_url', models.URLField(blank=True, max_length=500)),
                ('telegram_url', models.URLField(blank=True, max_length=500)),
                ('discord_url', models.URLField(blank=True, max_length=500)),
                ('demo_url', models.URLField(blank=True, max_length=500)),
                ('details', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('idle', 'Idle')], default='active', max_length=10)),
                ('order', models.PositiveIntegerField(default=0)),
                ('participants', models.ManyToManyField(blank=True, related_name='participating_projects', to=settings.AUTH_USER_MODEL)),
                ('related_contributions', models.ManyToManyField(blank=True, related_name='related_projects', to='contributions.contribution')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_projects', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['order', '-created_at'],
            },
        ),
        migrations.RunPython(copy_featured_builds_to_projects, copy_projects_to_featured_builds),
    ]
