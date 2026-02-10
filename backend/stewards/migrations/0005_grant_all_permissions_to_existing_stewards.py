from django.db import migrations


def grant_all_permissions(apps, schema_editor):
    """
    Grant all 4 actions on all contribution types to every existing Steward,
    preserving current behavior where all stewards have full permissions.
    """
    Steward = apps.get_model('stewards', 'Steward')
    ContributionType = apps.get_model('contributions', 'ContributionType')
    StewardPermission = apps.get_model('stewards', 'StewardPermission')

    actions = ['propose', 'accept', 'reject', 'request_more_info']
    stewards = Steward.objects.all()
    contribution_types = ContributionType.objects.all()

    permissions_to_create = []
    for steward in stewards:
        for ct in contribution_types:
            for action in actions:
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
            ignore_conflicts=True
        )


def reverse_grant(apps, schema_editor):
    """Remove all auto-granted permissions."""
    StewardPermission = apps.get_model('stewards', 'StewardPermission')
    StewardPermission.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('stewards', '0004_stewardpermission_reviewtemplate'),
        ('contributions', '0032_submittedcontribution_proposal_fields_submissionnote'),
    ]

    operations = [
        migrations.RunPython(grant_all_permissions, reverse_grant),
    ]
