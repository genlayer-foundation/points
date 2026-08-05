from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0020_unique_ban_appeal_per_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='can_view_role_sections',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'Allow read-only access to gated Builder, Validator, and Community '
                    'portal sections. This does not grant a role, interaction permissions, '
                    'or access to Steward tools.'
                ),
            ),
        ),
    ]
