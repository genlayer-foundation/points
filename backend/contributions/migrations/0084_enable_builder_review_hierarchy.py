from django.db import migrations


def enable_builder_review_hierarchy(apps, schema_editor):
    ContributionType = apps.get_model('contributions', 'ContributionType')
    ContributionType.objects.filter(category__slug='builder').update(
        requires_ai_review=True,
        escalation_threshold_points=400,
    )


def disable_builder_review_hierarchy(apps, schema_editor):
    ContributionType = apps.get_model('contributions', 'ContributionType')
    ContributionType.objects.filter(category__slug='builder').update(
        requires_ai_review=False,
        escalation_threshold_points=None,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0083_review_hierarchy_fields'),
    ]

    operations = [
        migrations.RunPython(
            enable_builder_review_hierarchy,
            disable_builder_review_hierarchy,
        ),
    ]
