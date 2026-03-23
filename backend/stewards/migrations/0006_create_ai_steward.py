from django.db import migrations


AI_STEWARD_EMAIL = 'genlayer-steward@genlayer.foundation'
AI_STEWARD_NAME = 'GenLayer Steward'

ACTIONS = ['propose', 'accept', 'reject', 'request_more_info']


def create_ai_steward(apps, schema_editor):
    """
    Create the AI steward user with full permissions on all contribution types.
    Used by the review_submissions management command for automated review.
    """
    User = apps.get_model('users', 'User')
    Steward = apps.get_model('stewards', 'Steward')
    StewardPermission = apps.get_model('stewards', 'StewardPermission')
    ContributionType = apps.get_model('contributions', 'ContributionType')

    # Create user (visible=False so it doesn't appear on leaderboard/public)
    user, created = User.objects.get_or_create(
        email=AI_STEWARD_EMAIL,
        defaults={
            'name': AI_STEWARD_NAME,
            'visible': False,
            'password': '!',  # Unusable password marker
        },
    )

    # Create steward profile
    steward, _ = Steward.objects.get_or_create(user=user)

    # Grant all permissions on all contribution types
    contribution_types = ContributionType.objects.all()
    permissions_to_create = []
    for ct in contribution_types:
        for action in ACTIONS:
            permissions_to_create.append(
                StewardPermission(
                    steward=steward,
                    contribution_type=ct,
                    action=action,
                )
            )

    if permissions_to_create:
        StewardPermission.objects.bulk_create(
            permissions_to_create,
            ignore_conflicts=True,
        )


def remove_ai_steward(apps, schema_editor):
    """Remove the AI steward user and all related data."""
    User = apps.get_model('users', 'User')
    User.objects.filter(email=AI_STEWARD_EMAIL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('stewards', '0005_grant_all_permissions_to_existing_stewards'),
        ('contributions', '0032_submittedcontribution_proposal_fields_submissionnote'),
        ('users', '0016_add_github_fields'),
    ]

    operations = [
        migrations.RunPython(create_ai_steward, remove_ai_steward),
    ]
