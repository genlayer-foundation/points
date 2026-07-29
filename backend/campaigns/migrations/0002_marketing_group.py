from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

MARKETING_GROUP_NAME = 'Marketing'

# (model, actions) the marketing staff group needs. Members additionally need
# is_staff=True, assigned manually per user.
MARKETING_PERMISSIONS = [
    ('marketingcampaign', ('add', 'change', 'view')),
    ('campaignlink', ('add', 'change', 'view')),
    ('campaignredirecthit', ('view',)),
    ('useracquisitionattribution', ('view',)),
]


def create_marketing_group(apps, schema_editor):
    # Permissions are normally created by post_migrate, which has not run yet
    # for this app on a fresh database; create them explicitly first.
    app_config = global_apps.get_app_config('campaigns')
    create_permissions(app_config, apps=apps, verbosity=0)

    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    group, _ = Group.objects.get_or_create(name=MARKETING_GROUP_NAME)
    for model, actions in MARKETING_PERMISSIONS:
        for action in actions:
            permission = Permission.objects.filter(
                content_type__app_label='campaigns',
                codename=f'{action}_{model}',
            ).first()
            if permission:
                group.permissions.add(permission)


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0001_initial'),
    ]

    operations = [
        # Reverse is a no-op: the forward path may have reused a pre-existing
        # Marketing group, so rollback must not delete it (or its members).
        migrations.RunPython(create_marketing_group, migrations.RunPython.noop),
    ]
