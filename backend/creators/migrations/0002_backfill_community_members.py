from django.db import migrations


def backfill_community_members(apps, schema_editor):
    Creator = apps.get_model('creators', 'Creator')
    Contribution = apps.get_model('contributions', 'Contribution')
    PoapClaim = apps.get_model('poaps', 'PoapClaim')

    user_ids = set(
        Contribution.objects.filter(
            contribution_type__category__slug='community',
        ).values_list('user_id', flat=True).distinct()
    )
    user_ids.update(
        PoapClaim.objects.filter(
            user__isnull=False,
        ).values_list('user_id', flat=True).distinct()
    )

    existing_user_ids = set(
        Creator.objects.filter(user_id__in=user_ids).values_list('user_id', flat=True)
    )
    missing_user_ids = user_ids - existing_user_ids

    Creator.objects.bulk_create(
        [Creator(user_id=user_id) for user_id in missing_user_ids],
        ignore_conflicts=True,
        batch_size=500,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('creators', '0001_initial'),
        ('contributions', '0061_featuredcontent_hero_placements'),
        ('poaps', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(backfill_community_members, migrations.RunPython.noop),
    ]
