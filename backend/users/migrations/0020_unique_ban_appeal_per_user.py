from django.db import migrations, models


def dedupe_ban_appeals(apps, schema_editor):
    BanAppeal = apps.get_model('users', 'BanAppeal')
    duplicate_user_ids = (
        BanAppeal.objects
        .values('user_id')
        .annotate(count=models.Count('id'))
        .filter(count__gt=1)
        .values_list('user_id', flat=True)
    )
    for user_id in duplicate_user_ids:
        keep = (
            BanAppeal.objects
            .filter(user_id=user_id)
            .order_by('-created_at', '-id')
            .first()
        )
        BanAppeal.objects.filter(user_id=user_id).exclude(pk=keep.pk).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_user_email_verified_at'),
    ]

    operations = [
        migrations.RunPython(dedupe_ban_appeals, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='banappeal',
            constraint=models.UniqueConstraint(fields=('user',), name='unique_ban_appeal_per_user'),
        ),
    ]
