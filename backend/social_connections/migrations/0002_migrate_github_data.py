"""Data migration: copy GitHub OAuth data from User model fields to GitHubConnection."""

import logging

from django.db import migrations
from django.utils import timezone

logger = logging.getLogger(__name__)


def migrate_github_data(apps, schema_editor):
    User = apps.get_model('users', 'User')
    GitHubConnection = apps.get_model('social_connections', 'GitHubConnection')

    # Check if the User model has the old GitHub fields
    user_fields = [f.name for f in User._meta.get_fields()]
    if 'github_user_id' not in user_fields:
        logger.info("No github_user_id field on User model — skipping migration")
        return

    users_with_github = User.objects.exclude(
        github_user_id=''
    ).exclude(
        github_user_id__isnull=True
    )

    count = users_with_github.count()
    if count == 0:
        logger.info("No users with GitHub connections to migrate")
        return

    connections = []
    for user in users_with_github.iterator():
        connections.append(GitHubConnection(
            user=user,
            platform_user_id=user.github_user_id,
            platform_username=user.github_username or '',
            access_token=user.github_access_token or '',
            refresh_token='',
            linked_at=user.github_linked_at or timezone.now(),
        ))

    GitHubConnection.objects.bulk_create(connections, ignore_conflicts=True)
    logger.info(f"Migrated {len(connections)} GitHub connections from User model")


class Migration(migrations.Migration):

    dependencies = [
        ('social_connections', '0001_initial'),
        ('users', '0016_add_github_fields'),
    ]

    operations = [
        migrations.RunPython(
            migrate_github_data,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
