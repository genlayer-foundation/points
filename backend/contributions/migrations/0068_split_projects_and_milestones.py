from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone
from django.utils.text import slugify


PROJECT_SLUG = 'projects'
LEGACY_PROJECT_SLUGS = [
    'projects-and-milestones',
    'projects-milestones',
    'project-milestone',
]
MILESTONE_SLUG = 'milestones'
ACTIONS = ['propose', 'accept', 'reject', 'request_more_info']


def _builder_category(Category):
    return Category.objects.get_or_create(
        slug='builder',
        defaults={
            'name': 'Builder',
            'description': 'Builder category',
        },
    )[0]


def _unique_slug(Project, title):
    base_slug = slugify(title)[:200] or 'project'
    slug = base_slug
    suffix = 2
    while Project.objects.filter(slug=slug).exists():
        suffix_text = f'-{suffix}'
        slug = f'{base_slug[:220 - len(suffix_text)]}{suffix_text}'
        suffix += 1
    return slug


def split_types_and_backfill_projects(apps, schema_editor):
    Category = apps.get_model('contributions', 'Category')
    ContributionType = apps.get_model('contributions', 'ContributionType')
    Contribution = apps.get_model('contributions', 'Contribution')
    SubmittedContribution = apps.get_model('contributions', 'SubmittedContribution')
    EvidenceURLType = apps.get_model('contributions', 'EvidenceURLType')
    Project = apps.get_model('projects', 'Project')
    GlobalLeaderboardMultiplier = apps.get_model('leaderboard', 'GlobalLeaderboardMultiplier')
    Steward = apps.get_model('stewards', 'Steward')
    StewardPermission = apps.get_model('stewards', 'StewardPermission')

    builder_category = _builder_category(Category)

    project_type = (
        ContributionType.objects.filter(slug=PROJECT_SLUG).first()
        or ContributionType.objects.filter(slug__in=LEGACY_PROJECT_SLUGS).first()
        or ContributionType.objects.filter(name__iexact='Projects and Milestones').first()
        or ContributionType.objects.filter(name__iexact='Project and Milestone').first()
    )
    if project_type:
        project_type.name = 'Projects'
        project_type.slug = PROJECT_SLUG
        project_type.category = project_type.category or builder_category
        project_type.is_submittable = True
        project_type.save(update_fields=['name', 'slug', 'category', 'is_submittable', 'updated_at'])
    else:
        project_type = ContributionType.objects.create(
            name='Projects',
            slug=PROJECT_SLUG,
            description='Submitted builder projects accepted into the Portal.',
            category=builder_category,
            min_points=50,
            max_points=500,
            is_submittable=True,
        )

    # Projects must come with a GitHub repository: reviewers evaluate the
    # repo, and later milestones for the project are reviewed against it.
    github_repo_type = EvidenceURLType.objects.filter(slug='github-repo').first()
    if github_repo_type:
        project_type.required_evidence_url_types.add(github_repo_type)

    milestone_type, _ = ContributionType.objects.get_or_create(
        slug=MILESTONE_SLUG,
        defaults={
            'name': 'Milestones',
            'description': 'Major updates or milestones for an accepted project.',
            'category': project_type.category or builder_category,
            'min_points': project_type.min_points,
            'max_points': project_type.max_points,
            'is_submittable': True,
            # Milestones are reviewed the same way as the project type: if
            # projects use the builder_project rubric flow, milestone reviews
            # must keep requiring and storing rubric reviews too.
            'review_flow': project_type.review_flow,
        },
    )

    if milestone_type.category_id is None:
        milestone_type.category = project_type.category or builder_category
        milestone_type.save(update_fields=['category', 'updated_at'])

    if not GlobalLeaderboardMultiplier.objects.filter(
        contribution_type=milestone_type,
    ).exists():
        project_multiplier = (
            GlobalLeaderboardMultiplier.objects
            .filter(contribution_type=project_type, valid_from__lte=timezone.now())
            .order_by('-valid_from')
            .first()
            or GlobalLeaderboardMultiplier.objects
            .filter(contribution_type=project_type)
            .order_by('-valid_from')
            .first()
        )
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=milestone_type,
            multiplier_value=(
                project_multiplier.multiplier_value
                if project_multiplier else 1
            ),
            valid_from=timezone.now(),
            description='Initial multiplier for milestones',
        )

    permissions = []
    for steward in Steward.objects.all():
        for contribution_type in (project_type, milestone_type):
            for action in ACTIONS:
                permissions.append(
                    StewardPermission(
                        steward=steward,
                        contribution_type=contribution_type,
                        action=action,
                    )
                )
    if permissions:
        StewardPermission.objects.bulk_create(permissions, ignore_conflicts=True)

    for contribution in Contribution.objects.filter(
        contribution_type=project_type,
        project__isnull=True,
    ).select_related('user').iterator(chunk_size=200):
        submission = SubmittedContribution.objects.filter(
            converted_contribution_id=contribution.id,
        ).first()
        project = Project.objects.filter(
            related_contributions=contribution,
        ).first()
        if project is None:
            title = (
                contribution.title
                or (submission.title if submission else '')
                or f"{contribution.user.name or contribution.user.address}'s Project"
            )
            description = contribution.notes or (submission.notes if submission else '')
            project = Project.objects.create(
                title=title[:200],
                slug=_unique_slug(Project, title),
                description=description[:2000],
                details=description,
                author=contribution.user.name or '',
                user_id=contribution.user_id,
                status='active',
            )
        project.participants.add(contribution.user_id)
        project.related_contributions.add(contribution.id)
        contribution.project_id = project.id
        contribution.save(update_fields=['project', 'updated_at'])
        if submission and submission.project_id is None:
            submission.project_id = project.id
            submission.save(update_fields=['project', 'updated_at'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0067_contributiontype_rubric_extra_points'),
        ('projects', '0002_ensure_project_participants_table'),
        ('leaderboard', '0014_add_referral_points_model'),
        ('stewards', '0010_builder_project_gate_templates'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='contribution',
            name='project',
            field=models.ForeignKey(blank=True, help_text='Project this contribution is attached to (used by project milestones)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='contributions', to='projects.project'),
        ),
        migrations.AddField(
            model_name='contribution',
            name='milestone_version',
            field=models.PositiveIntegerField(blank=True, help_text='Sequential milestone version within the linked project', null=True),
        ),
        migrations.AddField(
            model_name='submittedcontribution',
            name='project',
            field=models.ForeignKey(blank=True, help_text='Project this submission is attached to (required for milestones)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='submissions', to='projects.project'),
        ),
        migrations.AddField(
            model_name='submittedcontribution',
            name='milestone_version',
            field=models.PositiveIntegerField(blank=True, help_text='Sequential milestone version within the linked project', null=True),
        ),
        migrations.RunPython(split_types_and_backfill_projects, noop_reverse),
    ]
